"""
app/study_guide/mcq_generator.py
----------------------------------
Distributed Map-Reduce Multiple-Choice Question (MCQ) Generator (Phase 8).
Generates 2-3 granular, high-yield MCQs per text chunk, enforces strict schema validation,
retries once on malformed JSON, and deduplicates questions across overlapping chunks.
"""

import asyncio
import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from app.ai.models import get_llm_with_fallback
from app.rag.adhoc_loader import strip_repeated_headers_and_footers
from app.rag.loader import is_front_matter

logger = logging.getLogger("uvicorn")

# ── Configurable Named Tuning Constants ──────────────────────────────────────
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200
MCQS_PER_CHUNK = 2
QUESTION_SIMILARITY_THRESHOLD = 0.80


# ── Schemas ──────────────────────────────────────────────────────────────────
class MCQItem(BaseModel):
    """A single multiple choice question with 4 options and an answer explanation."""

    question: str = Field(description="The academic question prompt")
    options: List[str] = Field(description="Exactly 4 distinct answer choices")
    correct_index: int = Field(description="Index (0-3) of the correct answer")
    explanation: str = Field(description="Detailed academic rationale for the correct choice")


class ChunkMCQDeck(BaseModel):
    """Collection of MCQs generated for a single chunk."""

    questions: List[MCQItem] = Field(default_factory=list, description="List of generated MCQs")


# ── Prompts ──────────────────────────────────────────────────────────────────
CHUNK_MCQ_SYSTEM_PROMPT = """You are a rigorous university professor creating an exam question bank.
Generate exactly {count} academically challenging multiple-choice questions (MCQs) grounded strictly in the provided text chunk.

CRITICAL RULES:
1. Each question must test understanding of mechanics, definitions, or architectural trade-offs from THIS chunk.
2. Provide exactly 4 plausible options (A, B, C, D).
3. Specify `correct_index` as an integer from 0 to 3.
4. Output MUST be a valid JSON object matching this schema:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Why Option A is correct."
    }}
  ]
}}"""

CHUNK_MCQ_USER_PROMPT = """Generate {count} distinct MCQs based strictly on this text chunk:

--- CHUNK START ---
{chunk_text}
--- CHUNK END ---

Output ONLY valid JSON."""


def _parse_mcq_json(raw_text: str) -> Optional[List[MCQItem]]:
    """Parse JSON and validate against ChunkMCQDeck Pydantic schema."""
    cleaned = raw_text.strip()
    # Strip markdown code fencing if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            data = {"questions": data}
        validated = ChunkMCQDeck.model_validate(data)
        # Filter for valid questions with exactly 4 options and valid index
        valid_items = [
            q for q in validated.questions
            if len(q.options) == 4 and 0 <= q.correct_index <= 3 and q.question.strip()
        ]
        return valid_items if valid_items else None
    except Exception:
        return None


def _generate_chunk_mcqs(chunk_text: str, chunk_idx: int, total_chunks: int, count: int = MCQS_PER_CHUNK) -> List[MCQItem]:
    """Generate MCQs for a single chunk with a single retry on JSON parse failure."""
    logger.info(f"[MCQGenerator] Generating {count} MCQs for chunk {chunk_idx}/{total_chunks}...")
    llm = get_llm_with_fallback(temperature=0.3, max_tokens=1500)

    system_prompt = CHUNK_MCQ_SYSTEM_PROMPT.format(count=count)
    user_prompt = CHUNK_MCQ_USER_PROMPT.format(count=count, chunk_text=chunk_text)

    for attempt in range(2):
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt if attempt == 0 else f"{user_prompt}\nIMPORTANT: Reply with ONLY valid JSON."),
            ]
            response = llm.invoke(messages)
            raw_content = response.content if hasattr(response, "content") else str(response)

            items = _parse_mcq_json(str(raw_content))
            if items:
                logger.info(f"[MCQGenerator] Successfully generated {len(items)} MCQs from chunk {chunk_idx}/{total_chunks}")
                return items
            else:
                logger.warning(f"[MCQGenerator] Chunk {chunk_idx} JSON validation failed on attempt {attempt + 1}. Retrying...")
        except Exception as exc:
            logger.warning(f"[MCQGenerator] Chunk {chunk_idx} LLM call error (attempt {attempt + 1}): {exc}")

    logger.error(f"[MCQGenerator] Failed to generate valid MCQs for chunk {chunk_idx}/{total_chunks} after retry.")
    return []


def _is_similar_question(q1: str, q2: str, threshold: float = QUESTION_SIMILARITY_THRESHOLD) -> bool:
    """Check text similarity between two question prompts to deduplicate overlapping chunk outputs."""
    clean1 = re.sub(r"[^a-zA-Z0-9 ]", "", q1).lower().strip()
    clean2 = re.sub(r"[^a-zA-Z0-9 ]", "", q2).lower().strip()
    if clean1 == clean2:
        return True
    ratio = SequenceMatcher(None, clean1, clean2).ratio()
    return ratio >= threshold


def deduplicate_mcqs(mcqs: List[MCQItem], threshold: float = QUESTION_SIMILARITY_THRESHOLD) -> List[MCQItem]:
    """Deduplicate near-identical MCQs resulting from adjacent chunk overlap."""
    unique: List[MCQItem] = []
    for candidate in mcqs:
        is_dup = any(_is_similar_question(candidate.question, existing.question, threshold) for existing in unique)
        if not is_dup:
            unique.append(candidate)
        else:
            logger.debug(f"[MCQGenerator] Deduplicating similar question: {candidate.question[:60]}...")
    return unique


def generate_mcqs_for_document(
    pages_or_text: Union[str, List[Dict[str, Any]]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    mcqs_per_chunk: int = MCQS_PER_CHUNK,
    max_total_mcqs: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generate an exhaustive, evenly distributed quiz deck covering the ENTIRE document.

    Args:
        pages_or_text: Full document text or list of page dicts [{"page_number": int, "text": str}].
        chunk_size: Character length per chunk (default: 3000).
        chunk_overlap: Overlap between chunks (default: 200).
        mcqs_per_chunk: Number of MCQs generated per chunk (default: 2).
        max_total_mcqs: Optional cap on total questions returned.

    Returns:
        List of serialized MCQ dicts: [{"question": str, "options": list, "correct_index": int, "explanation": str}]
    """
    # 1. Sanitize pages and concatenate text
    total_pages = 0
    if isinstance(pages_or_text, list):
        total_pages = len(pages_or_text)
        cleaned_pages = strip_repeated_headers_and_footers(pages_or_text) if total_pages >= 2 else pages_or_text
        filtered_pages = [
            p.get("text", "") for p in cleaned_pages
            if p.get("text", "").strip() and not is_front_matter(p.get("text", ""))
        ]
        full_text = "\n\n".join(filtered_pages)
    else:
        full_text = str(pages_or_text).strip()

    if not full_text:
        return []

    # 2. Split with RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(full_text)
    total_chunks = len(chunks)
    logger.info(
        f"[MCQGenerator] Full text length: {len(full_text):,} chars ({total_pages} pages) "
        f"split into {total_chunks} chunks (chunk_size={chunk_size}, overlap={chunk_overlap})."
    )

    if total_chunks == 0:
        return []

    # 3. Generate MCQs per chunk with completeness tracking
    all_mcqs: List[MCQItem] = []
    empty_chunks = 0
    for idx, chunk in enumerate(chunks, start=1):
        chunk_items = _generate_chunk_mcqs(
            chunk_text=chunk,
            chunk_idx=idx,
            total_chunks=total_chunks,
            count=mcqs_per_chunk,
        )
        if not chunk_items:
            empty_chunks += 1
        all_mcqs.extend(chunk_items)

    successful_chunks = total_chunks - empty_chunks
    if empty_chunks > 0:
        logger.warning(
            f"[MCQGenerator] Completeness Warning: Expected {total_chunks} chunks to produce MCQs, "
            f"but {empty_chunks} chunk(s) yielded zero valid MCQs ({successful_chunks}/{total_chunks} successful)."
        )
    else:
        logger.info(
            f"[MCQGenerator] Completeness Check Passed: All {total_chunks} chunks yielded valid MCQs "
            f"across {total_pages or 1} pages ({len(all_mcqs)} questions total before deduplication)."
        )

    # 4. Deduplicate across chunks
    deduped = deduplicate_mcqs(all_mcqs, threshold=QUESTION_SIMILARITY_THRESHOLD)
    logger.info(f"[MCQGenerator] Total MCQs generated: {len(all_mcqs)}, after deduplication: {len(deduped)}")

    if max_total_mcqs and len(deduped) > max_total_mcqs:
        deduped = deduped[:max_total_mcqs]

    return [q.model_dump() for q in deduped]


async def generate_mcqs_for_document_async(
    pages_or_text: Union[str, List[Dict[str, Any]]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    mcqs_per_chunk: int = MCQS_PER_CHUNK,
    max_total_mcqs: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Asynchronous non-blocking wrapper around generate_mcqs_for_document."""
    return await asyncio.to_thread(
        generate_mcqs_for_document,
        pages_or_text,
        chunk_size,
        chunk_overlap,
        mcqs_per_chunk,
        max_total_mcqs,
    )


__all__ = [
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "MCQS_PER_CHUNK",
    "QUESTION_SIMILARITY_THRESHOLD",
    "MCQItem",
    "ChunkMCQDeck",
    "deduplicate_mcqs",
    "generate_mcqs_for_document",
    "generate_mcqs_for_document_async",
]
