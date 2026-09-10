"""
app/services/study_generator.py
---------------------------------
Structured Study Guide & MCQ Generation Engine using Google Gemini and Pydantic schemas.
Enforces strict JSON schema validation via LangChain's structured output.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("uvicorn")

# Default Gemini model verified to support structured output with high throughput
DEFAULT_STUDY_GEN_MODEL = "gemini-3.6-flash"

CANDIDATE_STUDY_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class MCQItem(BaseModel):
    """A single multiple choice question with 4 options and answer explanation."""

    question: str = Field(description="The question prompt")
    options: List[str] = Field(description="Exactly 4 distinct answer choices")
    correct_index: int = Field(description="Index (0-3) of the correct answer")
    explanation: str = Field(description="Detailed explanation why this option is correct")
    reference_page: Optional[int] = Field(default=None, description="Source page number")


class QuizDeck(BaseModel):
    """Collection of multiple choice questions forming an academic quiz."""

    title: str = Field(description="Quiz topic or title")
    questions: List[MCQItem] = Field(description="List of generated MCQs")


class StudyNotes(BaseModel):
    """High-yield structured study notes for academic revision and exam preparation."""

    executive_summary: str = Field(description="High-level overview of the material")
    key_concepts: List[Dict[str, str]] = Field(
        description="Dictionary list of concept -> definition, e.g. [{'concept': '...', 'definition': '...'}]"
    )
    formulas_and_theorems: List[str] = Field(
        description="List of mathematical formulas/theorems in LaTeX"
    )
    high_yield_revision_points: List[str] = Field(
        description="Cramming bullet points for exam prep"
    )


# ==============================================================================
# Helper LLM Factory
# ==============================================================================

def _get_llm(model_name: str = DEFAULT_STUDY_GEN_MODEL, temperature: Optional[float] = None) -> ChatGoogleGenerativeAI:
    """Instantiate and return a ChatGoogleGenerativeAI instance."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured in environment or settings. "
            "Please add GEMINI_API_KEY to your .env file."
        )
    kwargs: Dict[str, Any] = {
        "model": model_name,
        "google_api_key": api_key,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    return ChatGoogleGenerativeAI(**kwargs)


# ==============================================================================
# Multi-Provider Failovers (Groq)
# ==============================================================================

def _generate_with_groq_study_notes(context_text: str) -> Optional[StudyNotes]:
    """Failover generator using Groq's high-speed JSON inference."""
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        import json
        from groq import Groq

        client = Groq(api_key=api_key)
        prompt = (
            "You are an expert university professor and academic curriculum tutor. "
            "Analyze the following academic context and generate comprehensive, high-yield study notes. "
            "Respond ONLY with a valid JSON object matching the following structure:\n"
            "{\n"
            '  "executive_summary": "High-level overview string",\n'
            '  "key_concepts": [{"concept": "Name", "definition": "Clear explanation"}],\n'
            '  "formulas_and_theorems": ["Formula/Theorem in LaTeX notation"],\n'
            '  "high_yield_revision_points": ["Punchy bullet points for exam revision"]\n'
            "}\n\n"
            f"--- CONTEXT START ---\n{context_text.strip()[:14000]}\n--- CONTEXT END ---"
        )
        resp = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": "You are a university professor. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        return StudyNotes.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GroqFailover] Groq study notes fallback failed: {exc}")
        return None


def _generate_with_groq_quiz(context_text: str, num_questions: int = 5) -> Optional[QuizDeck]:
    """Failover generator for MCQs using Groq's high-speed JSON inference."""
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return None
    try:
        import json
        from groq import Groq

        client = Groq(api_key=api_key)
        prompt = (
            f"You are an expert university examiner. Generate exactly {num_questions} rigorous multiple-choice questions "
            "strictly grounded in the provided academic material. "
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "title": "Academic Subject Quiz",\n'
            '  "questions": [\n'
            "    {\n"
            '      "question": "Question text",\n'
            '      "options": ["Choice A", "Choice B", "Choice C", "Choice D"],\n'
            '      "correct_index": 0,\n'
            '      "explanation": "Why this specific choice is correct",\n'
            '      "reference_page": null\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"--- CONTEXT START ---\n{context_text.strip()[:14000]}\n--- CONTEXT END ---"
        )
        resp = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": "You are a university examiner. Respond ONLY with a valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_json = resp.choices[0].message.content
        data = json.loads(raw_json)
        return QuizDeck.model_validate(data)
    except Exception as exc:
        logger.warning(f"[GroqFailover] Groq MCQ quiz fallback failed: {exc}")
        return None


# ==============================================================================
# Generation Functions
# ==============================================================================

def generate_study_notes(
    context_text: str,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> StudyNotes:
    """
    Generate structured, high-yield study notes from syllabus or lecture context.

    Uses Google Gemini with structured output enforcing the `StudyNotes` schema.
    Automatically cascades through candidate models and Groq if rate limits occur.
    """
    if not context_text or not context_text.strip():
        raise ValueError("context_text cannot be empty or whitespace only.")

    models_to_try = [model_name] + [m for m in CANDIDATE_STUDY_MODELS if m != model_name]
    last_error = None

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model)
            structured_llm = llm.with_structured_output(StudyNotes)

            system_prompt = (
                "You are an expert university professor and academic curriculum tutor. "
                "Your task is to analyze the provided syllabus or academic context and generate "
                "comprehensive, high-yield study notes. "
                "Strictly adhere to the requested schema: extract executive summary, key concepts with clear definitions, "
                "mathematical formulas or engineering theorems in LaTeX notation, and punchy cramming revision points."
            )

            human_prompt = (
                "Please generate comprehensive study notes for the following academic context:\n\n"
                f"--- CONTEXT START ---\n{context_text.strip()}\n--- CONTEXT END ---"
            )

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            if isinstance(result, StudyNotes):
                return result
            elif isinstance(result, dict):
                return StudyNotes(**result)
            else:
                return StudyNotes.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_study_notes] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    # Attempt ultra-fast secondary provider failover (Groq)
    logger.info("[generate_study_notes] Gemini candidates exhausted; invoking Groq failover engine...")
    groq_result = _generate_with_groq_study_notes(context_text)
    if groq_result:
        return groq_result

    logger.error(f"[generate_study_notes] All candidate models failed. Last error: {last_error}")
    raise RuntimeError(f"Failed to generate structured study notes: {last_error}") from last_error


async def generate_study_notes_async(
    context_text: str,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> StudyNotes:
    """Asynchronous non-blocking wrapper around generate_study_notes."""
    return await asyncio.to_thread(generate_study_notes, context_text, model_name)


def generate_mcq_quiz(
    context_text: str,
    num_questions: int = 5,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> QuizDeck:
    """
    Generate an academic multiple-choice quiz from syllabus or course context.

    Uses Google Gemini with structured output enforcing the `QuizDeck` schema.
    Automatically cascades through candidate models and Groq if rate limits occur.
    """
    if not context_text or not context_text.strip():
        raise ValueError("context_text cannot be empty or whitespace only.")

    if num_questions < 1:
        raise ValueError("num_questions must be at least 1.")

    models_to_try = [model_name] + [m for m in CANDIDATE_STUDY_MODELS if m != model_name]
    last_error = None

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model)
            structured_llm = llm.with_structured_output(QuizDeck)

            system_prompt = (
                "You are an expert university examiner. Your task is to generate rigorous, "
                "academically challenging multiple-choice questions (MCQs) strictly grounded in the provided syllabus context.\n"
                f"Generate exactly {num_questions} questions.\n"
                "Requirements:\n"
                "- Each question must have exactly 4 distinct answer choices in 'options'.\n"
                "- 'correct_index' must be an integer between 0 and 3 indicating the zero-based index of the right option.\n"
                "- 'explanation' must clearly justify why that specific option is correct.\n"
                "- If a specific syllabus page number is explicitly referenced in the context, set 'reference_page' accordingly; otherwise null."
            )

            human_prompt = (
                f"Generate a quiz deck with {num_questions} questions based on the following material:\n\n"
                f"--- CONTEXT START ---\n{context_text.strip()}\n--- CONTEXT END ---"
            )

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            if isinstance(result, QuizDeck):
                return result
            elif isinstance(result, dict):
                return QuizDeck(**result)
            else:
                return QuizDeck.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_mcq_quiz] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    # Attempt ultra-fast secondary provider failover (Groq)
    logger.info("[generate_mcq_quiz] Gemini candidates exhausted; invoking Groq failover engine...")
    groq_result = _generate_with_groq_quiz(context_text, num_questions=num_questions)
    if groq_result:
        return groq_result

    logger.error(f"[generate_mcq_quiz] All candidate models failed. Last error: {last_error}")
    raise RuntimeError(f"Failed to generate structured MCQ quiz: {last_error}") from last_error


async def generate_mcq_quiz_async(
    context_text: str,
    num_questions: int = 5,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> QuizDeck:
    """Asynchronous non-blocking wrapper around generate_mcq_quiz."""
    return await asyncio.to_thread(generate_mcq_quiz, context_text, num_questions, model_name)
