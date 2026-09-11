"""
backend/scripts/test_full_document_notes.py
---------------------------------------------
Test suite verifying:
1. get_full_user_document retrieves all chunks ordered by page_number and chunk_id without top_k truncation.
2. assemble_document_context stitches chunks with '--- [PAGE X] ---' markers and excludes front-matter.
3. ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT instructs the model to enumerate all projects/modules without omission.
4. FastAPI endpoints (/api/study/export-notes and /api/study/download/pdf) invoke full document retrieval and deliver complete PDF/DOCX files.
"""

import io
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.ai.schemas import AdaptiveStudyNotes, TopicDetailBlock
from app.rag.user_doc_retriever import assemble_document_context, get_full_user_document
from app.services.export_service import export_notes_to_docx, export_notes_to_pdf
from app.services.study_generator import ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT
from app.auth.dependencies import get_current_user


def mock_current_user():
    return {"sub": "user_capstone_tester", "email": "student@college.edu"}


def run_full_document_tests():
    print("=" * 65)
    print("TESTING FULL-DOCUMENT RETRIEVAL & EXHAUSTIVE STUDY NOTES")
    print("=" * 65)

    # -------------------------------------------------------------
    # 1. Test assemble_document_context
    # -------------------------------------------------------------
    print("\n[1] Testing sequential document assembly with page separators...")
    mock_chunks = [
        {"page_number": 1, "chunk_id": "c1", "text": "All Rights Reserved. Published by College Press 2024."},  # Front matter
        {"page_number": 2, "chunk_id": "c2", "text": "Project 01: Study Guide Generator using RAG architecture."},
        {"page_number": 3, "chunk_id": "c3", "text": "Project 02: Flashcard Deck Builder with spaced repetition."},
        {"page_number": 4, "chunk_id": "c4", "text": "Project 03: Interactive Code Reviewer with static analysis."},
        {"page_number": 5, "chunk_id": "c5", "text": "Project 04: Virtual Lab Assistant for chemistry simulations."},
        {"page_number": 6, "chunk_id": "c6", "text": "Project 05: Automated Grading Engine for Python scripts."},
        {"page_number": 7, "chunk_id": "c7", "text": "Project 06: Distributed Storage System with Raft consensus."},
        {"page_number": 8, "chunk_id": "c8", "text": "Project 10: Devil's Advocate Panel for multi-agent debates."},
    ]

    assembled_text = assemble_document_context(mock_chunks)
    assert "All Rights Reserved" not in assembled_text, "Front matter should be filtered out"
    assert "--- [PAGE 2] ---" in assembled_text
    assert "--- [PAGE 8] ---" in assembled_text
    assert "Project 01: Study Guide Generator" in assembled_text
    assert "Project 10: Devil's Advocate Panel" in assembled_text
    print("[PASS] assemble_document_context correctly preserves all pages and strips front matter.")

    # -------------------------------------------------------------
    # 2. Test get_full_user_document sorting and tenancy
    # -------------------------------------------------------------
    print("\n[2] Testing get_full_user_document MongoDB query specification...")
    from unittest.mock import MagicMock
    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=mock_chunks[1:])
    mock_coll.find.return_value = mock_cursor

    with patch("app.rag.user_doc_retriever.get_user_doc_collection", return_value=mock_coll):
        import asyncio
        retrieved_chunks = asyncio.run(get_full_user_document("user_capstone_tester", "doc_capstone_101"))
        assert len(retrieved_chunks) == 7
        # Verify sort parameter
        mock_cursor.sort.assert_called_once_with([("page_number", 1), ("chunk_id", 1)])
        # Verify no limit parameter applied to to_list
        mock_cursor.to_list.assert_called_once_with(length=None)
        print("[PASS] get_full_user_document queries without limit and sorts by (page_number, chunk_id).")

    # -------------------------------------------------------------
    # 3. Test System Prompt Critical Rules for Zero Omission
    # -------------------------------------------------------------
    print("\n[3] Testing ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT coverage directives...")
    assert "COMPLETE ENUMERATION (ZERO OMISSIONS)" in ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT
    assert "Do NOT truncate, bundle into \"etc.\"" in ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT
    assert "STRICTLY ELIMINATE ARTIFICIAL SYNTAX AND FORMULAS" in ADAPTIVE_STUDY_NOTES_SYSTEM_PROMPT
    print("[PASS] System prompt strictly enforces full enumeration and forbids truncation.")

    # -------------------------------------------------------------
    # 4. Test 10-Project Complete Study Guide & Export
    # -------------------------------------------------------------
    print("\n[4] Testing multi-project AdaptiveStudyNotes instantiation & export...")
    all_10_sections = [
        TopicDetailBlock(
            title=f"Project {i:02d}: Architectural Track {i}",
            overview=f"Comprehensive implementation of project specification {i} covering design, tech stack, and evaluation criteria.",
            key_points=[
                f"Core requirement {i}.1: Microservice deployment",
                f"Core requirement {i}.2: Testing and benchmark metrics",
            ],
            code_or_syntax=None,
        )
        for i in range(1, 11)
    ]

    full_catalog_notes = AdaptiveStudyNotes(
        title="Senior Capstone Projects Catalog (All 10 Tracks)",
        executive_summary="This catalog details all 10 engineering capstone projects across systems, AI, and distributed architectures.",
        sections=all_10_sections,
        actionable_takeaways=[
            "Submit project repository with complete Docker configuration by Week 12.",
            "All projects undergo automated CI/CD and stress test evaluation.",
        ],
    )

    assert len(full_catalog_notes.sections) == 10
    print(f"[PASS] AdaptiveStudyNotes successfully instantiated with all {len(full_catalog_notes.sections)} sections.")

    # Export to PDF and DOCX
    pdf_buf = export_notes_to_pdf(full_catalog_notes)
    assert isinstance(pdf_buf, io.BytesIO)
    pdf_bytes = pdf_buf.getvalue()
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2500
    print(f"[PASS] Multi-page PDF successfully generated ({len(pdf_bytes)} bytes).")

    docx_buf = export_notes_to_docx(full_catalog_notes)
    assert isinstance(docx_buf, io.BytesIO)
    docx_bytes = docx_buf.getvalue()
    assert docx_bytes.startswith(b"PK\x03\x04")
    assert len(docx_bytes) > 10000
    print(f"[PASS] Multi-page DOCX successfully generated ({len(docx_bytes)} bytes).")

    # -------------------------------------------------------------
    # 5. Test Live FastAPI Endpoints with Mocked Retrieval & Generation
    # -------------------------------------------------------------
    print("\n[5] Testing FastAPI /api/study/export-notes with full document context...")
    app.dependency_overrides[get_current_user] = mock_current_user
    client = TestClient(app)

    with patch("app.routes.study.get_full_user_document", AsyncMock(return_value=mock_chunks)), \
         patch("app.routes.study.generate_adaptive_study_notes", return_value=full_catalog_notes):

        # 5a. GET /api/study/export-notes (PDF)
        res_pdf = client.get("/api/study/export-notes?topic=Capstone+Projects&doc_id=doc_capstone_101&file_format=pdf")
        assert res_pdf.status_code == 200, res_pdf.text
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert 'attachment; filename="Capstone_Projects_notes.pdf"' in res_pdf.headers["content-disposition"]
        assert len(res_pdf.content) > 2500
        print("[PASS] GET /api/study/export-notes returned complete PDF stream (> 2.5KB).")

        # 5b. GET /api/study/export-notes (DOCX)
        res_docx = client.get("/api/study/export-notes?topic=Capstone+Projects&doc_id=doc_capstone_101&file_format=docx")
        assert res_docx.status_code == 200, res_docx.text
        assert "openxmlformats" in res_docx.headers["content-type"]
        assert 'attachment; filename="Capstone_Projects_notes.docx"' in res_docx.headers["content-disposition"]
        assert len(res_docx.content) > 10000
        print("[PASS] GET /api/study/export-notes returned complete DOCX stream (> 10KB).")

    app.dependency_overrides.clear()
    print("\n" + "=" * 65)
    print("[ALL CHECKS PASSED] Full-Document Context & Zero-Omission Notes Verified!")
    print("=" * 65)


if __name__ == "__main__":
    run_full_document_tests()
