"""
app/services/evaluation_service.py
----------------------------------
Service for generating university Part-A (2-mark) conceptual tests and
performing semantic AI evaluation of student written answers against rubrics.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("uvicorn")

DEFAULT_EVAL_MODEL = "gemini-3.5-flash-lite"
CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
]


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class TwoMarkQuestion(BaseModel):
    question_id: str = Field(description="Unique question identifier, e.g. Q1, Q2")
    question: str = Field(description="Direct, 2-mark conceptual question")
    model_answer: str = Field(description="Ideal 2-3 sentence answer worth full marks")
    key_points: List[str] = Field(description="Exactly 2 key concepts/points (each worth 1 mark)")


class TwoMarkTestDeck(BaseModel):
    topic: str = Field(description="Subject or lecture title")
    total_marks: int = Field(description="Total marks (e.g. 10 for 5 questions)")
    questions: List[TwoMarkQuestion] = Field(description="List of 2-mark conceptual questions")


class EvaluationResult(BaseModel):
    question_id: str = Field(description="Question identifier, e.g. Q1")
    score_awarded: int = Field(description="Score awarded: 0, 1, or 2 marks")
    max_marks: int = Field(default=2, description="Maximum possible marks for this question")
    points_covered: List[str] = Field(default_factory=list, description="Rubric points the student correctly addressed")
    points_missed: List[str] = Field(default_factory=list, description="Rubric points the student missed")
    feedback: str = Field(description="Constructive feedback explaining the score and what was missing")
    model_answer: str = Field(default="", description="Reference answer for the student to review")


# ==============================================================================
# Prompts
# ==============================================================================

TWO_MARK_TEST_SYSTEM_PROMPT = """You are a university engineering professor setting a Part-A (2-mark) exam.
Generate precise, conceptual questions requiring concise, technical definitions, formulas, or trade-offs.
Each question must have exactly 2 clear scoring criteria (each worth 1 mark).
Strictly ignore publishers, copyright, or author metadata. Focus purely on foundational engineering principles and substantive course concepts.
"""

TWO_MARK_TEST_USER_PROMPT = """Document Context:
{context}

Task:
Generate a Part-A test with exactly {count} distinct 2-mark conceptual questions based strictly on the provided context.
Rules:
- Assign question_id sequentially: "Q1", "Q2", etc.
- Each question must be rigorous and require specific technical knowledge, trade-offs, or precise definitions.
- For each question, provide an ideal 2-3 sentence model_answer.
- For each question, provide key_points: a list containing EXACTLY 2 distinct points (each worth 1 mark in evaluation).
- Set total_marks to {total_marks} ({count} * 2).
- Set topic to a concise, academic title reflecting the material.
"""

EVALUATE_SYSTEM_PROMPT = """You are a strict but fair academic evaluator grading a university Part-A (2-mark) question.
Grading Rules:
- Award 2 marks if BOTH rubric points are clearly explained or present via core technical keywords/concepts.
- Award 1 mark if ONLY ONE rubric point is adequately covered.
- Award 0 marks if the student answer is completely off-topic, incorrect, missing, or purely superficial filler.
- Evaluate SEMANTICALLY: accept conceptually correct wording and technical synonyms rather than demanding verbatim phrase matching.
- Provide constructive feedback highlighting exact technical terms or concepts that were missing.
"""

EVALUATE_USER_PROMPT = """Question:
{question}

Model Answer:
{model_answer}

Rubric Key Points (1 mark each):
{key_points}

Student's Written Answer:
{student_answer}

Evaluate the student's answer against the rubric key points and output the assessment.
"""


# ==============================================================================
# Helper LLM Factory
# ==============================================================================

def _get_llm(model_name: str = DEFAULT_EVAL_MODEL, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Please add GEMINI_API_KEY to your .env file."
        )
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
    )


# ==============================================================================
# Generation & Evaluation Implementation
# ==============================================================================

def generate_two_mark_test(
    context: str,
    count: int = 5,
    model_name: str = DEFAULT_EVAL_MODEL,
) -> TwoMarkTestDeck:
    """
    Synchronously generate a TwoMarkTestDeck from context using Gemini with structured output.
    """
    if not context or not context.strip():
        raise ValueError("Context cannot be empty for 2-mark test generation.")

    models_to_try = [model_name] + [m for m in CANDIDATE_MODELS if m != model_name]
    last_error = None

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model, temperature=0.3)
            structured_llm = llm.with_structured_output(TwoMarkTestDeck)

            system_prompt = TWO_MARK_TEST_SYSTEM_PROMPT
            human_prompt = TWO_MARK_TEST_USER_PROMPT.format(
                context=context.strip()[:30000],
                count=count,
                total_marks=count * 2,
            )

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])

            if isinstance(result, TwoMarkTestDeck):
                return result
            elif isinstance(result, dict):
                return TwoMarkTestDeck.model_validate(result)
            else:
                return TwoMarkTestDeck.model_validate(result)
        except Exception as exc:
            logger.warning(f"[generate_two_mark_test] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    raise RuntimeError(f"Failed to generate 2-mark test: {last_error}") from last_error


async def generate_two_mark_test_async(
    context: str,
    count: int = 5,
    model_name: str = DEFAULT_EVAL_MODEL,
) -> TwoMarkTestDeck:
    """
    Asynchronously generate a TwoMarkTestDeck using Gemini with structured output.
    """
    return await asyncio.to_thread(
        generate_two_mark_test,
        context=context,
        count=count,
        model_name=model_name,
    )


def evaluate_student_answer(
    question: str,
    model_answer: str,
    key_points: List[str],
    student_answer: str,
    question_id: str = "Q1",
    model_name: str = DEFAULT_EVAL_MODEL,
) -> EvaluationResult:
    """
    Synchronously evaluate a student's written response against a 2-mark question rubric.
    Awards 0, 1, or 2 marks with points covered/missed breakdown and constructive feedback.
    """
    if not student_answer or not student_answer.strip():
        # Immediate 0 for empty submission
        return EvaluationResult(
            question_id=question_id,
            score_awarded=0,
            max_marks=2,
            points_covered=[],
            points_missed=key_points or ["Point 1", "Point 2"],
            feedback="No answer was provided.",
            model_answer=model_answer,
        )

    formatted_points = "\n".join(f"- Point {idx+1}: {pt}" for idx, pt in enumerate(key_points))

    models_to_try = [model_name] + [m for m in CANDIDATE_MODELS if m != model_name]
    last_error = None

    for model in models_to_try:
        try:
            llm = _get_llm(model_name=model, temperature=0.1)
            structured_llm = llm.with_structured_output(EvaluationResult)

            system_prompt = EVALUATE_SYSTEM_PROMPT
            human_prompt = EVALUATE_USER_PROMPT.format(
                question=question,
                model_answer=model_answer,
                key_points=formatted_points,
                student_answer=student_answer.strip(),
            )

            result = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])

            eval_res: EvaluationResult
            if isinstance(result, EvaluationResult):
                eval_res = result
            elif isinstance(result, dict):
                eval_res = EvaluationResult.model_validate(result)
            else:
                eval_res = EvaluationResult.model_validate(result)

            eval_res.question_id = question_id
            if not eval_res.model_answer:
                eval_res.model_answer = model_answer
            # Clamp score between 0 and 2
            eval_res.score_awarded = max(0, min(2, eval_res.score_awarded))
            return eval_res

        except Exception as exc:
            logger.warning(f"[evaluate_student_answer] Model '{model}' failed: {exc}. Trying fallback...")
            last_error = exc

    raise RuntimeError(f"Failed to evaluate student answer: {last_error}") from last_error


async def evaluate_student_answer_async(
    question: str,
    model_answer: str,
    key_points: List[str],
    student_answer: str,
    question_id: str = "Q1",
    model_name: str = DEFAULT_EVAL_MODEL,
) -> EvaluationResult:
    """
    Asynchronously evaluate a student's written response against a 2-mark question rubric.
    """
    return await asyncio.to_thread(
        evaluate_student_answer,
        question=question,
        model_answer=model_answer,
        key_points=key_points,
        student_answer=student_answer,
        question_id=question_id,
        model_name=model_name,
    )


__all__ = [
    "TwoMarkQuestion",
    "TwoMarkTestDeck",
    "EvaluationResult",
    "generate_two_mark_test",
    "generate_two_mark_test_async",
    "evaluate_student_answer",
    "evaluate_student_answer_async",
]
