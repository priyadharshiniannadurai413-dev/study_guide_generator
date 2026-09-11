"""
app/routes/web_research.py
--------------------------
FastAPI router for standalone Web Research & Fetch MCP clean content extraction:
- POST /api/web/fetch → Fetch URL, strip boilerplate, and return clean article Markdown
- POST /api/web/ask   → Answer questions grounded strictly in the extracted webpage content
"""

import logging
from typing import Any, Dict, Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.web_content_service import get_web_content_service, validate_public_url
from app.auth.dependencies import get_current_user

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/web", tags=["web_research"])


class WebFetchRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL (must be http:// or https://)")


class WebAskRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL containing the reference text")
    question: str = Field(..., description="Specific student inquiry about the webpage content")


class WebStudyNotesRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL to synthesize study notes from")
    topic: Optional[str] = Field(default=None, description="Optional focus topic or chapter within the webpage")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Target academic difficulty level ('beginner', 'intermediate', 'advanced')",
    )


def _validate_url(url: str) -> str:
    """Validate HTTP/HTTPS URL format and enforce SSRF protections."""
    try:
        return validate_public_url(url)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )


@router.post("/fetch")
async def fetch_webpage(
    payload: WebFetchRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch webpage using Fetch MCP, strip navigation, menus, and footer boilerplate,
    and return clean educational article Markdown with extraction metadata.
    """
    clean_url = _validate_url(payload.url)
    service = get_web_content_service()

    try:
        doc = await service.get_clean_web_document(clean_url)
        return {
            "success": True,
            "url": doc.url,
            "title": doc.title,
            "content": doc.content,
            "word_count": doc.word_count,
            "extraction_method": doc.extraction_method,
            "extraction_confidence": doc.extraction_confidence,
            "retrieved_at": doc.retrieved_at,
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        logger.warning(f"[WebResearchRoute] Extraction failed for '{clean_url}': {run_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err),
        )
    except Exception as exc:
        logger.error(f"[WebResearchRoute] Unexpected error fetching '{clean_url}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve or process the requested webpage.",
        )


@router.post("/ask")
async def ask_webpage_question(
    payload: WebAskRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Answer a question grounded strictly in the extracted webpage content.
    Applies token safety for large pages and returns source attribution.
    """
    clean_url = _validate_url(payload.url)
    question_clean = (payload.question or "").strip()
    if not question_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    service = get_web_content_service()
    try:
        result = await service.answer_question_from_web(clean_url, question_clean)
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        logger.warning(f"[WebResearchRoute] Q&A extraction failed for '{clean_url}': {run_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err),
        )
    except Exception as exc:
        logger.error(f"[WebResearchRoute] Q&A generation error for '{clean_url}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate an answer from the webpage content.",
        )


@router.post("/notes")
async def generate_web_study_notes(
    payload: WebStudyNotesRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch webpage using Fetch MCP, strip boilerplate, and synthesize high-yield
    structured AdaptiveStudyNotes calibrated to the selected difficulty.
    """
    clean_url = _validate_url(payload.url)
    service = get_web_content_service()

    try:
        return await service.generate_study_notes_from_web(
            url=clean_url,
            topic=payload.topic,
            difficulty=payload.difficulty,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        logger.warning(f"[WebResearchRoute] Study notes generation failed for '{clean_url}': {run_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err),
        )
    except Exception as exc:
        logger.error(f"[WebResearchRoute] Unexpected error generating notes for '{clean_url}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate study notes from the webpage content.",
        )


__all__ = ["router"]
