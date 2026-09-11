"""
app/study_guide/summarizer.py
-------------------------------
Map-Reduce Document Summarization Engine (Phase 8).
Splits long extracted documents into discrete chunks, maps them to granular summaries,
and recursively reduces the summaries into one cohesive final overview.
"""

import asyncio
import logging
from typing import Any, Dict, List, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.models import get_llm_with_fallback
from app.rag.adhoc_loader import strip_repeated_headers_and_footers
from app.rag.loader import is_front_matter

logger = logging.getLogger("uvicorn")

# ── Configurable Named Tuning Constants ──────────────────────────────────────
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200
REDUCE_BATCH_SIZE = 10
MAX_DIRECT_REDUCE_CHUNKS = 15


# ── Prompts ──────────────────────────────────────────────────────────────────
MAP_SYSTEM_PROMPT = """You are an elite academic professor and technical summarizer.
Your task is to summarize the provided chunk of an educational or technical document.
Focus strictly on core technical principles, operational mechanics, definitions, rules, and milestones.
Do not hallucinate content not present in the chunk. Be dense, factual, and clear."""

MAP_USER_PROMPT = """Extract the high-yield core concepts, definitions, and takeaways from this section:

--- CHUNK START ---
{chunk_text}
--- CHUNK END ---

Provide a structured, dense summary of this chunk (3-5 concise bullet points or a dense paragraph)."""


REDUCE_SYSTEM_PROMPT = """You are a senior curriculum architect and textbook editor.
Your objective is to synthesize multiple section summaries into one unified, cohesive, and comprehensive study guide summary.
Ensure all distinct modules, chapters, tracks, and principles across the entire document are clearly synthesized."""

REDUCE_USER_PROMPT = """Combine and synthesize the following section summaries into one cohesive, holistic final summary.
Organize with a clear executive overview followed by key thematic areas:

--- SECTION SUMMARIES ---
{combined_summaries}
--- END SECTION SUMMARIES ---

Produce a clean, professional, and exhaustive summary covering all topics represented above."""


def _map_chunk_summary(chunk_text: str, chunk_idx: int, total_chunks: int) -> str:
    """Execute MAP step on a single text chunk using the primary LLM with automatic failover."""
    logger.info(f"[Summarizer] Processing chunk {chunk_idx}/{total_chunks} ({len(chunk_text):,} chars)...")
    try:
        llm = get_llm_with_fallback(temperature=0.2, max_tokens=1024)
        messages = [
            SystemMessage(content=MAP_SYSTEM_PROMPT),
            HumanMessage(content=MAP_USER_PROMPT.format(chunk_text=chunk_text)),
        ]
        response = llm.invoke(messages)
        summary = response.content if hasattr(response, "content") else str(response)
        logger.info(f"[Summarizer] Summarized chunk {chunk_idx}/{total_chunks}")
        return str(summary).strip()
    except Exception as exc:
        logger.warning(f"[Summarizer] Map step failed on chunk {chunk_idx}/{total_chunks}: {exc}")
        return f"[Section {chunk_idx} Notes: {chunk_text[:300]}...]"


async def _map_chunk_summary_async(chunk_text: str, chunk_idx: int, total_chunks: int) -> str:
    """Asynchronous wrapper for single chunk mapping."""
    return await asyncio.to_thread(_map_chunk_summary, chunk_text, chunk_idx, total_chunks)


def _reduce_summaries(summaries: List[str]) -> str:
    """Execute REDUCE step on a batch of summaries using the primary LLM with fallback."""
    combined = "\n\n".join(f"[Section {i+1}]\n{s}" for i, s in enumerate(summaries))
    logger.info(f"[Summarizer] Reducing {len(summaries)} summaries ({len(combined):,} chars)...")
    try:
        llm = get_llm_with_fallback(temperature=0.2, max_tokens=2048)
        messages = [
            SystemMessage(content=REDUCE_SYSTEM_PROMPT),
            HumanMessage(content=REDUCE_USER_PROMPT.format(combined_summaries=combined)),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        return str(content).strip()
    except Exception as exc:
        logger.error(f"[Summarizer] Reduce step failed: {exc}")
        return combined


def _recursive_reduce(summaries: List[str], batch_size: int = REDUCE_BATCH_SIZE) -> str:
    """
    Recursively batch reduce steps when chunk summaries risk exceeding safe prompt bounds (>15 chunks).
    Combines summaries in groups of `batch_size` until a single cohesive summary is achieved.
    """
    if not summaries:
        return "No content available to summarize."

    if len(summaries) == 1:
        return summaries[0]

    # If within direct reduce threshold, do a single final reduce
    if len(summaries) <= MAX_DIRECT_REDUCE_CHUNKS:
        return _reduce_summaries(summaries)

    logger.info(f"[Summarizer] Intermediate reduce: Batching {len(summaries)} summaries in groups of {batch_size}...")
    intermediate_summaries = []
    for i in range(0, len(summaries), batch_size):
        batch = summaries[i : i + batch_size]
        reduced_batch = _reduce_summaries(batch)
        intermediate_summaries.append(reduced_batch)

    # Recurse until one unified summary remains
    return _recursive_reduce(intermediate_summaries, batch_size=batch_size)


def summarize_document(
    pages_or_text: Union[str, List[Dict[str, Any]]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> str:
    """
    Generate an exhaustive study summary of a multi-page document using the Map-Reduce pattern.

    Args:
        pages_or_text: Full document text or list of page dicts [{"page_number": int, "text": str}].
        chunk_size: Target character length per chunk (default: 3000).
        chunk_overlap: Overlapping characters between adjacent chunks (default: 200).

    Returns:
        One cohesive, comprehensive markdown summary.
    """
    # 1. Sanitize pages and concatenate text
    total_pages = 0
    if isinstance(pages_or_text, list):
        total_pages = len(pages_or_text)
        # Apply generic running header/footer stripping if document has multiple pages
        cleaned_pages = strip_repeated_headers_and_footers(pages_or_text) if total_pages >= 2 else pages_or_text
        filtered_pages = [
            p.get("text", "") for p in cleaned_pages
            if p.get("text", "").strip() and not is_front_matter(p.get("text", ""))
        ]
        full_text = "\n\n".join(filtered_pages)
    else:
        full_text = str(pages_or_text).strip()

    if not full_text:
        return "Document is empty or contains only non-substantive front matter."

    # 2. Split with RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(full_text)
    total_chunks = len(chunks)
    logger.info(
        f"[Summarizer] Full text length: {len(full_text):,} chars ({total_pages} pages) "
        f"split into {total_chunks} chunks (chunk_size={chunk_size}, overlap={chunk_overlap})."
    )

    if total_chunks == 0:
        return "No text chunks generated for summarization."

    # 3. MAP STEP: Process each chunk
    chunk_summaries: List[str] = []
    failed_chunks = 0
    for idx, chunk in enumerate(chunks, start=1):
        summary = _map_chunk_summary(chunk_text=chunk, chunk_idx=idx, total_chunks=total_chunks)
        if summary.startswith("[Section") and "Notes:" in summary:
            failed_chunks += 1
        chunk_summaries.append(summary)

    # Completeness check: compare processed chunks against expected split count
    processed_count = len(chunk_summaries)
    if failed_chunks > 0:
        logger.warning(
            f"[Summarizer] Completeness Warning: Expected {total_chunks} chunks, but "
            f"{failed_chunks} chunks failed or used fallback notes ({processed_count}/{total_chunks} processed)."
        )
    else:
        logger.info(
            f"[Summarizer] Completeness Check Passed: Successfully processed {processed_count}/{total_chunks} "
            f"chunks end-to-end across {total_pages or 1} pages."
        )

    # 4. REDUCE STEP: Combine all chunk summaries recursively
    final_summary = _recursive_reduce(chunk_summaries, batch_size=REDUCE_BATCH_SIZE)
    return final_summary


async def summarize_document_async(
    pages_or_text: Union[str, List[Dict[str, Any]]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> str:
    """Asynchronous non-blocking wrapper around summarize_document."""
    return await asyncio.to_thread(summarize_document, pages_or_text, chunk_size, chunk_overlap)


__all__ = [
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "REDUCE_BATCH_SIZE",
    "MAX_DIRECT_REDUCE_CHUNKS",
    "summarize_document",
    "summarize_document_async",
]
