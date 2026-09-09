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
DEFAULT_STUDY_GEN_MODEL = "gemini-3.5-flash"


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

def _get_llm(model_name: str = DEFAULT_STUDY_GEN_MODEL, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Instantiate and return a ChatGoogleGenerativeAI instance."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured in environment or settings. "
            "Please add GEMINI_API_KEY to your .env file."
        )
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
    )


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

    Args:
        context_text: Text content from syllabus chunks, notes, or query retrieval.
        model_name: Name of the Gemini model to invoke.

    Returns:
        StudyNotes instance populated with executive summary, key concepts, formulas, and revision points.

    Raises:
        ValueError: If context_text is empty or API key is not configured.
        RuntimeError: If LLM generation or structured output parsing fails.
    """
    if not context_text or not context_text.strip():
        raise ValueError("context_text cannot be empty or whitespace only.")

    llm = _get_llm(model_name=model_name, temperature=0.2)
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

    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        if isinstance(result, StudyNotes):
            return result
        elif isinstance(result, dict):
            return StudyNotes(**result)
        else:
            # Attempt parsing if result is a raw model or unexpected container
            return StudyNotes.model_validate(result)
    except Exception as exc:
        logger.error(f"[generate_study_notes] Generation failed: {exc}")
        raise RuntimeError(f"Failed to generate structured study notes: {exc}") from exc


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

    Args:
        context_text: Academic text or syllabus content to generate questions from.
        num_questions: Number of MCQs to generate (default: 5).
        model_name: Name of the Gemini model to invoke.

    Returns:
        QuizDeck instance containing topic title and list of MCQItem objects.

    Raises:
        ValueError: If context_text is empty or num_questions < 1.
        RuntimeError: If LLM generation or structured output parsing fails.
    """
    if not context_text or not context_text.strip():
        raise ValueError("context_text cannot be empty or whitespace only.")

    if num_questions < 1:
        raise ValueError("num_questions must be at least 1.")

    llm = _get_llm(model_name=model_name, temperature=0.3)
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

    try:
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
        logger.error(f"[generate_mcq_quiz] Quiz generation failed: {exc}")
        raise RuntimeError(f"Failed to generate structured MCQ quiz: {exc}") from exc


async def generate_mcq_quiz_async(
    context_text: str,
    num_questions: int = 5,
    model_name: str = DEFAULT_STUDY_GEN_MODEL,
) -> QuizDeck:
    """Asynchronous non-blocking wrapper around generate_mcq_quiz."""
    return await asyncio.to_thread(generate_mcq_quiz, context_text, num_questions, model_name)
