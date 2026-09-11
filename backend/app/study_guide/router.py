"""
app/study_guide/router.py
--------------------------
FastAPI router for ad-hoc PDF study guide generation (Phase 8).
Accepts an uploaded PDF file, runs full-document extraction, and executes
Map-Reduce summarization and distributed MCQ generation covering the entire file.
"""

import logging
import os
import tempfile
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.rag.adhoc_loader import load_adhoc_pdf
from app.study_guide.mcq_generator import generate_mcqs_for_document
from app.study_guide.summarizer import summarize_document

logger = logging.getLogger("uvicorn")

router = APIRouter(tags=["study-guide"])


@router.post("/study-guide/upload", status_code=status.HTTP_200_OK)
@router.post("/api/study-guide/upload", status_code=status.HTTP_200_OK)
async def upload_study_guide_document(
    file: UploadFile = File(..., description="PDF document for ad-hoc study guide & MCQ generation"),
) -> Dict[str, Any]:
    """
    Ingest an ad-hoc PDF and generate a complete study guide (cohesive summary & distributed MCQs).
    Uses Map-Reduce architecture to ensure full document coverage without truncation.
    """
    filename = file.filename or "uploaded_study_guide.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are supported.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file: Not a valid PDF document.",
        )

    # Save to a temporary file for extraction
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        pages = load_adhoc_pdf(tmp_path)
        total_pages = len(pages)
        if total_pages == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to extract readable pages from the provided PDF.",
            )

        logger.info(f"[StudyGuide] Generating Map-Reduce summary for {filename} ({total_pages} pages)...")
        summary = summarize_document(pages)

        logger.info(f"[StudyGuide] Generating Map-Reduce MCQs for {filename} ({total_pages} pages)...")
        mcqs = generate_mcqs_for_document(pages)

        return {
            "filename": filename,
            "total_pages": total_pages,
            "summary": summary,
            "mcqs": mcqs,
            "total_mcqs": len(mcqs),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[StudyGuide] Failed to process study guide for {filename}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Study guide generation failed: {exc}",
        )
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass


__all__ = ["router"]
