"""
app/routes/study.py
-------------------
FastAPI router for dedicated study generation endpoints:
- POST /api/study/notes: Generates high-yield structured StudyNotes from document context
- POST /api/study/mcq: Generates structured QuizDeck (MCQs) from document context
Strictly scoped to the authenticated Clerk user.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.rag.rag_pipeline import run_rag_query
from app.rag.user_doc_retriever import get_user_doc_context
from app.services.study_generator import (
    QuizDeck,
    StudyNotes,
    generate_mcq_quiz_async,
    generate_study_notes_async,
)

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/study", tags=["study"])


class StudyNotesRequest(BaseModel):
    doc_id: str = Field(description="UUID of uploaded document or 'syllabus'")
    topic: Optional[str] = Field(default=None, description="Optional focus topic within the document")


class MCQRequest(BaseModel):
    doc_id: str = Field(description="UUID of uploaded document or 'syllabus'")
    count: int = Field(default=5, ge=1, le=20, description="Number of MCQs to generate (1-20)")
    topic: Optional[str] = Field(default=None, description="Optional focus topic within the document")


async def _fetch_context(user_id: str, doc_id: str, topic: Optional[str] = None) -> str:
    """Fetch academic text context from either user document or global syllabus."""
    query = topic or "core concepts, architecture, formulas, and high-yield revision topics"

    if doc_id.lower() == "syllabus":
        rag_res = await run_rag_query(query, top_k=6)
        context = rag_res.get("answer_context", "")
        if not context:
            chunks = rag_res.get("retrieved_chunks", [])
            context = "\n\n".join(c.get("text", "") for c in chunks if c.get("text"))
        return context

    # User uploaded document
    chunks = await get_user_doc_context(user_id=user_id, doc_id=doc_id, query=query, top_k=8)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No readable content found for document '{doc_id}'. Please check doc_id or upload again.",
        )

    formatted = "\n\n".join(
        f"[Page {c.get('page_number', 1)}]\n{c.get('text', '').strip()}"
        for c in chunks
        if c.get("text")
    )
    return formatted


@router.post("/notes", response_model=StudyNotes)
async def generate_notes(
    request: StudyNotesRequest,
    current_user: dict = Depends(get_current_user),
) -> StudyNotes:
    """
    Generate high-yield structured study notes from an uploaded PDF or syllabus.
    Returns executive summary, key concepts, formulas/theorems, and revision points.
    """
    user_id = current_user["sub"]
    if not request.doc_id or not request.doc_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id cannot be empty.",
        )

    context_text = await _fetch_context(user_id, request.doc_id.strip(), request.topic)
    if not context_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract sufficient text from document to generate study notes.",
        )

    try:
        notes = await generate_study_notes_async(context_text)
        return notes
    except Exception as exc:
        logger.error(f"[StudyRoute] Study notes generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate study notes: {exc}",
        )


@router.post("/mcq", response_model=QuizDeck)
async def generate_mcqs(
    request: MCQRequest,
    current_user: dict = Depends(get_current_user),
) -> QuizDeck:
    """
    Generate an academic multiple-choice quiz from an uploaded PDF or syllabus.
    Returns exactly 4 distinct options per question with correct answer index and explanation.
    """
    user_id = current_user["sub"]
    if not request.doc_id or not request.doc_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id cannot be empty.",
        )

    context_text = await _fetch_context(user_id, request.doc_id.strip(), request.topic)
    if not context_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract sufficient text from document to generate quiz questions.",
        )

    try:
        quiz = await generate_mcq_quiz_async(context_text, num_questions=request.count)
        return quiz
    except Exception as exc:
        logger.error(f"[StudyRoute] MCQ generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate MCQ quiz: {exc}",
        )


__all__ = ["router"]
