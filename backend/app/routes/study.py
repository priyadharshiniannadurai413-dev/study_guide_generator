"""
app/routes/study.py
-------------------
FastAPI router for dedicated study generation endpoints:
- POST /api/study/notes: Generates high-yield structured StudyNotes via LangGraph
- POST /api/study/mcq: Generates structured QuizDeck (MCQs) via LangGraph
"""

import io
import json
import logging
import re
from typing import Any, Dict, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.ai.chat_service import get_chat_service
from app.ai.schemas import AdaptiveStudyNotes, QuizDeck, StudyNotes, TopicDetailBlock
from app.auth.dependencies import get_current_user
from app.db.mongodb import get_user_doc_collection
from app.rag.user_doc_retriever import (
    assemble_document_context,
    get_full_user_document,
    get_user_doc_context,
)
from app.rag.vector_store import get_vector_store
from app.services.export_service import (
    export_mcqs_to_csv,
    export_notes_to_docx,
    export_notes_to_pdf,
    export_pack_to_pdf,
)
from app.services.evaluation_service import (
    EvaluationResult,
    TwoMarkQuestion,
    TwoMarkTestDeck,
    evaluate_student_answer_async,
    generate_two_mark_test_async,
)
from app.services.study_generator import (
    CompleteStudyPack,
    ConceptBlock,
    TopicStudyNotes,
    generate_adaptive_study_notes,
    generate_adaptive_study_notes_async,
    generate_complete_study_pack_async,
    generate_topic_study_notes_async,
)

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/study", tags=["study"])


class StudyNotesRequest(BaseModel):
    doc_id: str = Field(description="UUID of uploaded document or 'syllabus'")
    topic: Optional[str] = Field(default=None, description="Optional focus topic within the document")


class TopicNotesRequest(BaseModel):
    topic: str = Field(description="Specific technical topic, e.g. 'Pointers in C' or 'Fourier Transform'")
    doc_id: Optional[str] = Field(default=None, description="Optional doc_id of user document or 'syllabus'")


class MCQRequest(BaseModel):
    doc_id: str = Field(description="UUID of uploaded document or 'syllabus'")
    count: int = Field(default=5, ge=1, le=20, description="Number of MCQs to generate (1-20)")
    topic: Optional[str] = Field(default=None, description="Optional focus topic within the document")


class ExportNotesRequest(BaseModel):
    notes: Optional[Dict[str, Any]] = Field(default=None, description="Pre-generated TopicStudyNotes or StudyNotes payload")
    topic: Optional[str] = Field(default=None, description="Topic name if generating on the fly")
    doc_id: Optional[str] = Field(default=None, description="Optional doc_id if generating on the fly")


class GeneratePackRequest(BaseModel):
    doc_id: Optional[str] = Field(default=None, description="UUID of uploaded document or 'syllabus'")
    pasted_text: Optional[str] = Field(default=None, description="Raw study notes or syllabus text")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Target academic difficulty level ('beginner', 'intermediate', 'advanced')"
    )


class ExportPackRequest(BaseModel):
    pack: Optional[Dict[str, Any]] = Field(default=None, description="Pre-generated CompleteStudyPack payload")
    title: Optional[str] = None
    difficulty: Optional[str] = None
    concise_summary: Optional[str] = None
    suggested_study_order: Optional[list] = None
    glossary: Optional[list] = None
    mcqs: Optional[list] = None
    short_answers: Optional[list] = None
    doc_id: Optional[str] = None
    pasted_text: Optional[str] = None


class GenerateTestRequest(BaseModel):
    doc_id: Optional[str] = Field(default=None, description="UUID of uploaded document or 'syllabus'")
    pasted_text: Optional[str] = Field(default=None, description="Pasted lecture notes or syllabus text")
    question_count: int = Field(default=5, ge=1, le=20, description="Number of 2-mark questions to generate")


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(description="Unique question identifier, e.g. Q1")
    question: str = Field(description="The question prompt")
    model_answer: str = Field(description="The reference model answer")
    key_points: list[str] = Field(description="Scoring criteria list (2 points)")
    student_answer: str = Field(description="Student's written response")


async def _fetch_context_for_topic(user_id: str, topic: str, doc_id: Optional[str] = None) -> str:
    """Retrieve complete context chunks for a topic or document from user documents or syllabus vectors."""
    if doc_id and doc_id.lower() != "syllabus":
        try:
            chunks = await get_full_user_document(user_id=user_id, doc_id=doc_id)
            if chunks:
                full_ctx = assemble_document_context(chunks)
                if full_ctx:
                    return full_ctx
        except Exception as exc:
            logger.warning(f"[StudyRoute] Full document retrieval error: {exc}")

    # If no user doc chunks found or doc_id is syllabus/unspecified, retrieve from syllabus vectors
    context_snippets: list[str] = []
    try:
        vstore = get_vector_store()
        res = await vstore.retrieve(query=topic, top_k=8)
        for m in res.get("matches", []):
            txt = m.get("text", "").strip()
            if txt:
                context_snippets.append(txt)
    except Exception as exc:
        logger.warning(f"[StudyRoute] Syllabus retrieval notice: {exc}")

    if not context_snippets:
        # Fallback to topic prompt
        return f"Academic subject topic: {topic}. Core engineering curriculum principles and practical implementations."

    return "\n\n".join(context_snippets)


def _safe_filename(title: str, ext: str) -> str:
    """Sanitize title for Content-Disposition filename."""
    cleaned = re.sub(r"[^a-zA-Z0-9_\- ]", "", title).strip().replace(" ", "_")
    base = cleaned[:50] if cleaned else "study_notes"
    return f"{base}.{ext}"


@router.post("/topic-notes")
async def generate_topic_notes(
    request: TopicNotesRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate student-friendly, high-yield topic study notes.
    Outputs structured TopicStudyNotes with ConceptBlocks, syntax/formulas, and pitfalls.
    """
    user_id = current_user.get("sub", "anonymous")
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic cannot be empty.",
        )

    context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic, doc_id=request.doc_id)

    try:
        notes = await generate_topic_study_notes_async(topic=topic, context_text=context_text)
        return notes.model_dump()
    except Exception as exc:
        logger.error(f"[StudyRoute] Topic notes generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate topic study notes: {exc}",
        )


@router.post("/notes")
async def generate_notes(
    request: StudyNotesRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate high-yield structured study notes from an uploaded PDF or syllabus.
    Invokes the LangGraph StudyNotes agent via the Supervisor workflow,
    falling back to direct topic-notes generation if requested.
    """
    user_id = current_user.get("sub", "anonymous")
    if not request.doc_id or not request.doc_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id cannot be empty.",
        )

    # Build the user query for the graph
    topic = request.topic or "comprehensive study notes covering all key topics"
    user_prompt = f"Generate study notes for: {topic}"

    chat_service = get_chat_service()

    try:
        result = await chat_service.invoke(
            user_prompt=user_prompt,
            user_id=user_id,
            doc_id=request.doc_id.strip(),
            route="study_notes",
        )

        # If the graph produced structured study_notes, return them
        study_notes = result.get("study_notes")
        if study_notes:
            try:
                # Convert or validate to AdaptiveStudyNotes
                if "sections" in study_notes:
                    return AdaptiveStudyNotes.model_validate(study_notes).model_dump()
                if "concepts" in study_notes:
                    return TopicStudyNotes.model_validate(study_notes).to_adaptive_study_notes().model_dump()
                validated = StudyNotes.model_validate(study_notes)
                return validated.to_adaptive_study_notes().model_dump()
            except Exception:
                return study_notes

        # Fallback: try direct adaptive generator
        context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic, doc_id=request.doc_id)
        adaptive_notes = await generate_adaptive_study_notes_async(topic=topic, context_text=context_text)
        return adaptive_notes.model_dump()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[StudyRoute] Study notes generation failed: {exc}")
        # Direct fallback
        try:
            context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic, doc_id=request.doc_id)
            adaptive_notes = await generate_adaptive_study_notes_async(topic=topic, context_text=context_text)
            return adaptive_notes.model_dump()
        except Exception as direct_exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate study notes: {direct_exc}",
            )


@router.get("/export-notes")
async def export_study_notes(
    topic: Optional[str] = Query("Study Guide"),
    doc_id: Optional[str] = Query(None),
    file_format: Literal["pdf", "docx"] = Query("pdf"),
    current_user: dict = Depends(get_current_user),
):
    """
    Direct export endpoint for study notes in PDF or DOCX format.
    Streams an in-memory file buffer directly to the client.
    """
    topic_clean = topic.strip() if (topic and topic.strip()) else "Study Guide"
    raw_context = ""
    if doc_id and doc_id.lower() != "syllabus":
        try:
            chunks = await get_full_user_document(
                user_id=current_user.get("sub", "anonymous"),
                doc_id=doc_id,
            )
            raw_context = assemble_document_context(chunks)
        except Exception as exc:
            logger.warning(f"[StudyRoute] Error retrieving full doc chunks for export: {exc}")

    if not raw_context:
        raw_context = await _fetch_context_for_topic(
            user_id=current_user.get("sub", "anonymous"),
            topic=topic_clean,
            doc_id=doc_id,
        )

    notes = generate_adaptive_study_notes(topic=topic_clean, context=raw_context)

    clean_filename = "".join(c for c in topic_clean if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")[:30]
    if not clean_filename:
        clean_filename = "study_notes"

    if file_format == "pdf":
        buf = export_notes_to_pdf(notes)
        media_type = "application/pdf"
        filename = f"{clean_filename}_notes.pdf"
    else:
        buf = export_notes_to_docx(notes)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{clean_filename}_notes.docx"

    return StreamingResponse(
        buf,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/export/pdf")
@router.post("/download/pdf")
async def export_pdf(
    request: ExportNotesRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Export study notes as a beautifully formatted PDF document.
    Returns in-memory PDF buffer with application/pdf Content-Type.
    """
    user_id = current_user.get("sub", "anonymous")

    # If notes payload is provided, directly render
    if request.notes:
        try:
            pdf_buf = export_notes_to_pdf(request.notes)
            title = (
                request.notes.get("title")
                or request.notes.get("topic_title")
                or request.topic
                or "Study_Notes"
            )
            filename = _safe_filename(title, "pdf")
            return StreamingResponse(
                pdf_buf,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition",
                },
            )
        except Exception as exc:
            logger.error(f"[StudyRoute] PDF export error from payload: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notes payload for PDF export: {exc}",
            )

    # Otherwise generate on the fly if topic is provided
    topic = request.topic or "Study Notes"
    context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic, doc_id=request.doc_id)
    notes = await generate_adaptive_study_notes_async(topic=topic, context_text=context_text)

    pdf_buf = export_notes_to_pdf(notes)
    filename = _safe_filename(notes.title or notes.topic_title or topic, "pdf")
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/download/pdf")
@router.get("/export/pdf")
async def download_pdf_get(
    topic: Optional[str] = "Study Guide",
    doc_id: Optional[str] = "syllabus",
    current_user: dict = Depends(get_current_user),
):
    """Direct GET download endpoint for study notes PDF."""
    user_id = current_user.get("sub", "anonymous")
    topic_clean = topic or "Study Guide"
    context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic_clean, doc_id=doc_id)
    notes = await generate_adaptive_study_notes_async(topic=topic_clean, context_text=context_text)

    pdf_buf = export_notes_to_pdf(notes)
    filename = _safe_filename(notes.title or notes.topic_title or topic_clean, "pdf")
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/export/docx")
@router.post("/download/docx")
async def export_docx(
    request: ExportNotesRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Export study notes as a cleanly formatted Word (.docx) document.
    Returns in-memory DOCX buffer with openxmlformats Content-Type.
    """
    user_id = current_user.get("sub", "anonymous")

    # If notes payload is provided, directly render
    if request.notes:
        try:
            docx_buf = export_notes_to_docx(request.notes)
            title = (
                request.notes.get("title")
                or request.notes.get("topic_title")
                or request.topic
                or "Study_Notes"
            )
            filename = _safe_filename(title, "docx")
            return StreamingResponse(
                docx_buf,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition",
                },
            )
        except Exception as exc:
            logger.error(f"[StudyRoute] DOCX export error from payload: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notes payload for DOCX export: {exc}",
            )

    # Otherwise generate on the fly if topic is provided
    topic = request.topic or "Study Notes"
    context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic, doc_id=request.doc_id)
    notes = await generate_adaptive_study_notes_async(topic=topic, context_text=context_text)

    docx_buf = export_notes_to_docx(notes)
    filename = _safe_filename(notes.title or notes.topic_title or topic, "docx")
    return StreamingResponse(
        docx_buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/download/docx")
@router.get("/export/docx")
async def download_docx_get(
    topic: Optional[str] = "Study Guide",
    doc_id: Optional[str] = "syllabus",
    current_user: dict = Depends(get_current_user),
):
    """Direct GET download endpoint for study notes Word (.docx) document."""
    user_id = current_user.get("sub", "anonymous")
    topic_clean = topic or "Study Guide"
    context_text = await _fetch_context_for_topic(user_id=user_id, topic=topic_clean, doc_id=doc_id)
    notes = await generate_adaptive_study_notes_async(topic=topic_clean, context_text=context_text)

    docx_buf = export_notes_to_docx(notes)
    filename = _safe_filename(notes.title or notes.topic_title or topic_clean, "docx")
    return StreamingResponse(
        docx_buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/mcq")
async def generate_mcqs(
    request: MCQRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate an academic multiple-choice quiz from an uploaded PDF or syllabus.
    Invokes the LangGraph MCQ agent via the Supervisor workflow.
    """
    user_id = current_user.get("sub", "anonymous")
    if not request.doc_id or not request.doc_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id cannot be empty.",
        )

    topic = request.topic or "key concepts and important topics"
    user_prompt = f"Generate {request.count} MCQs for: {topic}"

    chat_service = get_chat_service()

    try:
        result = await chat_service.invoke(
            user_prompt=user_prompt,
            user_id=user_id,
            doc_id=request.doc_id.strip(),
            num_questions=request.count,
            route="mcq",
        )

        quiz_deck = result.get("quiz_deck")
        if quiz_deck:
            try:
                validated = QuizDeck.model_validate(quiz_deck)
                return validated.model_dump()
            except Exception:
                return quiz_deck

        final_response = result.get("final_response", "")
        try:
            parsed = json.loads(final_response)
            validated = QuizDeck.model_validate(parsed)
            return validated.model_dump()
        except (json.JSONDecodeError, Exception):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate structured MCQ quiz.",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[StudyRoute] MCQ generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate MCQ quiz: {exc}",
        )


@router.post("/generate-pack")
async def generate_pack(
    request: GeneratePackRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a complete, high-yield Study Pack from an uploaded PDF (doc_id) or pasted text.
    Produces:
    - Concise summary notes
    - Exactly 20 practice MCQs with explanations and options
    - Exactly 5 short-answer questions with model answers and evaluation rubrics
    - Key terms glossary
    - Suggested study order roadmap
    Calibrated to difficulty ('beginner', 'intermediate', 'advanced').
    """
    user_id = current_user.get("sub", "anonymous")
    context: str = ""

    if request.pasted_text and request.pasted_text.strip():
        context = request.pasted_text.strip()
    elif request.doc_id and request.doc_id.strip():
        doc_id = request.doc_id.strip()
        if doc_id.lower() != "syllabus":
            chunks = await get_full_user_document(user_id=user_id, doc_id=doc_id)
            if not chunks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document '{doc_id}' not found or access denied for current user.",
                )
            context = assemble_document_context(chunks)
        else:
            context = await _fetch_context_for_topic(
                user_id=user_id,
                topic="Comprehensive course syllabus overview",
                doc_id="syllabus",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either doc_id or pasted_text must be provided.",
        )

    if not context or not context.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document text content available to generate study pack.",
        )

    try:
        pack = await generate_complete_study_pack_async(
            context=context,
            difficulty=request.difficulty,
        )
        return pack.model_dump()
    except Exception as exc:
        logger.error(f"[StudyRoute] Complete study pack generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate study pack: {exc}",
        )


@router.post("/export-pack/pdf")
async def export_pack_pdf(
    request: ExportPackRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Export full Study Pack (Summary, Roadmap, Glossary, 20 MCQs, 5 Short Answers)
    to a formatted ReportLab PDF document.
    """
    user_id = current_user.get("sub", "anonymous")
    pack_dict: Optional[Dict[str, Any]] = None

    if request.pack:
        pack_dict = request.pack
    elif request.mcqs or request.concise_summary:
        raw_dict = request.model_dump(exclude_unset=True)
        raw_dict.pop("pack", None)
        raw_dict.pop("doc_id", None)
        raw_dict.pop("pasted_text", None)
        pack_dict = raw_dict

    if not pack_dict:
        if request.pasted_text or request.doc_id:
            gen_req = GeneratePackRequest(
                doc_id=request.doc_id,
                pasted_text=request.pasted_text,
                difficulty=request.difficulty or "intermediate",
            )
            gen_res = await generate_pack(gen_req, current_user=current_user)
            pack_dict = gen_res
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Study pack data or valid source (doc_id / pasted_text) must be provided for PDF export.",
            )

    try:
        pdf_buf = export_pack_to_pdf(pack_dict)
        title = pack_dict.get("title") or "Complete_Study_Pack"
        filename = _safe_filename(title, "pdf")
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as exc:
        logger.error(f"[StudyRoute] Export pack PDF failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export study pack to PDF: {exc}",
        )


@router.post("/export-pack/csv")
async def export_pack_csv(
    request: ExportPackRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Export 20 MCQs from a Study Pack as a CSV formatted for flashcard import
    (Anki / Quizlet compatible: Question, Options, Correct Answer, Explanation).
    """
    user_id = current_user.get("sub", "anonymous")
    mcqs_list = None

    if request.pack and "mcqs" in request.pack:
        mcqs_list = request.pack["mcqs"]
    elif request.mcqs:
        mcqs_list = request.mcqs
    elif request.pasted_text or request.doc_id:
        gen_req = GeneratePackRequest(
            doc_id=request.doc_id,
            pasted_text=request.pasted_text,
            difficulty=request.difficulty or "intermediate",
        )
        gen_res = await generate_pack(gen_req, current_user=current_user)
        mcqs_list = gen_res.get("mcqs", [])

    if not mcqs_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No MCQs found in the provided payload or generated pack.",
        )

    try:
        csv_stream = export_mcqs_to_csv(mcqs_list)
        csv_bytes = io.BytesIO(csv_stream.getvalue().encode("utf-8"))
        filename = "mcqs_flashcards.csv"
        return StreamingResponse(
            csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as exc:
        logger.error(f"[StudyRoute] Export MCQs CSV failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export MCQs to CSV: {exc}",
        )


@router.post("/generate-test", response_model=TwoMarkTestDeck)
async def generate_test(
    req: GenerateTestRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a Part-A (2-mark) conceptual test based strictly on uploaded material or pasted text.
    Enforces tenant isolation by scoping doc_id lookups to current_user["sub"].
    """
    user_id = current_user.get("sub", "anonymous")
    raw_context = ""

    if req.doc_id and req.doc_id.strip():
        doc_id = req.doc_id.strip()
        if doc_id.lower() != "syllabus":
            chunks = await get_full_user_document(user_id=user_id, doc_id=doc_id)
            if not chunks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document '{doc_id}' not found or access denied for current user.",
                )
            raw_context = assemble_document_context(chunks) or "\n\n".join([c.get("text", "") for c in chunks])
        else:
            raw_context = await _fetch_context_for_topic(
                user_id=user_id,
                topic="Comprehensive course overview for Part-A conceptual questions",
                doc_id="syllabus",
            )
    elif req.pasted_text and req.pasted_text.strip():
        raw_context = req.pasted_text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either doc_id or pasted_text.",
        )

    if not raw_context or not raw_context.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content found in document or text to generate test.",
        )

    try:
        test_deck = await generate_two_mark_test_async(
            context=raw_context,
            count=req.question_count,
        )
        return test_deck
    except Exception as exc:
        logger.error(f"[StudyRoute] Generate 2-mark test failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate 2-mark test: {exc}",
        )


@router.post("/evaluate-answer", response_model=EvaluationResult)
async def evaluate_answer(
    req: SubmitAnswerRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Semantically evaluate a student's written answer against the 2-mark rubric.
    Awards 0, 1, or 2 marks with points covered/missed breakdown and constructive feedback.
    """
    try:
        result = await evaluate_student_answer_async(
            question=req.question,
            model_answer=req.model_answer,
            key_points=req.key_points,
            student_answer=req.student_answer,
            question_id=req.question_id,
        )
        result.question_id = req.question_id
        return result
    except Exception as exc:
        logger.error(f"[StudyRoute] Evaluate answer failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate student answer: {exc}",
        )


__all__ = ["router"]
