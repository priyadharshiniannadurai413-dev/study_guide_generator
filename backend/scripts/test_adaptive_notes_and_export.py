"""
backend/scripts/test_adaptive_notes_and_export.py
--------------------------------------------------
Test suite verifying:
1. Dynamic AdaptiveStudyNotes Pydantic schema (eliminating mandatory syntax/formulas and fake checkboxes).
2. Robust in-memory PDF export (reportlab) without crashing on null/optional fields.
3. Robust in-memory Word (.docx) export (python-docx) without crashing on null/optional fields.
4. Live API endpoints for PDF/DOCX downloads via FastAPI TestClient (GET & POST).
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.ai.schemas import AdaptiveStudyNotes, TopicDetailBlock
from app.services.export_service import export_notes_to_docx, export_notes_to_pdf
from app.services.study_generator import generate_adaptive_study_notes
from app.auth.dependencies import get_current_user


def mock_current_user():
    return {"sub": "test_user_adaptive", "email": "test@adaptive.edu"}


def run_tests():
    print("=" * 60)
    print("TESTING ADAPTIVE STUDY NOTES & DOCUMENT EXPORT SUITE")
    print("=" * 60)

    # -------------------------------------------------------------
    # 1. Schema Validation (No code, no syntax, no fake checkboxes)
    # -------------------------------------------------------------
    print("\n[1] Testing AdaptiveStudyNotes schema with non-code document...")
    sample_notes = AdaptiveStudyNotes(
        title="Distributed Systems Project Catalog",
        executive_summary=(
            "This catalog specifies the architectural milestones for building an enterprise "
            "distributed storage engine. Emphasis is on replicated consensus and partition tolerance."
        ),
        sections=[
            TopicDetailBlock(
                title="Milestone 1: Consensus Engine",
                overview="Implement Raft leader election and log replication with persistent state machine.",
                key_points=[
                    "Heartbeat intervals must be between 150ms and 300ms",
                    "Leader must commit entries once replicated on quorum",
                    "Handle split-vote election timeouts cleanly",
                ],
                code_or_syntax=None,  # Intentionally None: no syntax/formula present in source!
            ),
            TopicDetailBlock(
                title="Milestone 2: Distributed Key-Value Store",
                overview="Layer a distributed KV storage engine on top of the consensus cluster.",
                key_points=[
                    "Linearizable reads and writes",
                    "Snapshot compaction to truncate consensus log",
                ],
                code_or_syntax="put(key, value) -> OK | ERR_NOT_LEADER",  # Optional pseudo-code
            ),
        ],
        actionable_takeaways=[
            "All nodes must persist log state before acknowledging quorum RPCs.",
            "Submissions require passing 50 iterations of Jepsen network partition tests.",
            "Final capstone review includes a live 3-node chaos testing demonstration.",
        ],
    )

    assert sample_notes.title == "Distributed Systems Project Catalog"
    assert len(sample_notes.sections) == 2
    assert sample_notes.sections[0].code_or_syntax is None
    # Verify backward-compatibility properties
    assert sample_notes.topic_title == sample_notes.title
    assert sample_notes.quick_summary == sample_notes.executive_summary
    assert len(sample_notes.key_takeaways) == 3
    print("[PASS] AdaptiveStudyNotes instantiated and backward-compatibility fields verified.")

    # -------------------------------------------------------------
    # 2. PDF Export Test (Without syntax/pitfalls crash)
    # -------------------------------------------------------------
    print("\n[2] Testing PDF Export Engine (reportlab) with adaptive notes...")
    pdf_buf = export_notes_to_pdf(sample_notes)
    assert isinstance(pdf_buf, (bytes, io.BytesIO))
    pdf_bytes = pdf_buf.getvalue() if isinstance(pdf_buf, io.BytesIO) else pdf_buf
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
    print(f"[PASS] PDF generated successfully ({len(pdf_bytes)} bytes, header: {pdf_bytes[:5]}).")

    # -------------------------------------------------------------
    # 3. DOCX Export Test (Without syntax/pitfalls crash)
    # -------------------------------------------------------------
    print("\n[3] Testing Word Export Engine (python-docx) with adaptive notes...")
    docx_buf = export_notes_to_docx(sample_notes)
    assert isinstance(docx_buf, (bytes, io.BytesIO))
    docx_bytes = docx_buf.getvalue() if isinstance(docx_buf, io.BytesIO) else docx_buf
    assert len(docx_bytes) > 5000
    assert docx_bytes.startswith(b"PK\x03\x04")
    print(f"[PASS] DOCX generated successfully ({len(docx_bytes)} bytes, zip magic header: {docx_bytes[:4]}).")

    # -------------------------------------------------------------
    # 4. Live FastAPI TestClient (GET and POST export/download)
    # -------------------------------------------------------------
    print("\n[4] Testing FastAPI Download & Export Endpoints...")
    app.dependency_overrides[get_current_user] = mock_current_user
    client = TestClient(app)

    # 4a. POST /api/study/export/pdf with notes payload
    res_pdf_post = client.post("/api/study/export/pdf", json={"notes": sample_notes.model_dump()})
    assert res_pdf_post.status_code == 200, res_pdf_post.text
    assert res_pdf_post.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res_pdf_post.headers["content-disposition"]
    print("[PASS] POST /api/study/export/pdf returned 200 with attachment.")

    # 4b. POST /api/study/download/pdf alias
    res_pdf_dl_post = client.post("/api/study/download/pdf", json={"notes": sample_notes.model_dump()})
    assert res_pdf_dl_post.status_code == 200
    print("[PASS] POST /api/study/download/pdf alias returned 200 with attachment.")

    # 4c. POST /api/study/export/docx with notes payload
    res_docx_post = client.post("/api/study/export/docx", json={"notes": sample_notes.model_dump()})
    assert res_docx_post.status_code == 200, res_docx_post.text
    assert "openxmlformats" in res_docx_post.headers["content-type"]
    assert "attachment; filename=" in res_docx_post.headers["content-disposition"]
    print("[PASS] POST /api/study/export/docx returned 200 with attachment.")

    # 4d. POST /api/study/download/docx alias
    res_docx_dl_post = client.post("/api/study/download/docx", json={"notes": sample_notes.model_dump()})
    assert res_docx_dl_post.status_code == 200
    print("[PASS] POST /api/study/download/docx alias returned 200 with attachment.")

    # 4e. Mock generator for direct GET download tests to avoid external LLM latency
    from unittest.mock import patch

    with patch("app.routes.study.generate_adaptive_study_notes", return_value=sample_notes), \
         patch("app.routes.study.generate_adaptive_study_notes_async", return_value=sample_notes):

        # 4e1. GET /api/study/export-notes?topic=Capstone+Projects&file_format=pdf
        res_export_pdf = client.get("/api/study/export-notes?topic=Capstone+Projects&file_format=pdf")
        assert res_export_pdf.status_code == 200, res_export_pdf.text
        assert res_export_pdf.headers["content-type"] == "application/pdf"
        assert 'attachment; filename="Capstone_Projects_notes.pdf"' in res_export_pdf.headers["content-disposition"]
        assert len(res_export_pdf.content) > 1000
        print("[PASS] GET /api/study/export-notes (pdf) returned 200 with readable PDF stream.")

        # 4e2. GET /api/study/export-notes?topic=Capstone+Projects&file_format=docx
        res_export_docx = client.get("/api/study/export-notes?topic=Capstone+Projects&file_format=docx")
        assert res_export_docx.status_code == 200, res_export_docx.text
        assert "openxmlformats" in res_export_docx.headers["content-type"]
        assert 'attachment; filename="Capstone_Projects_notes.docx"' in res_export_docx.headers["content-disposition"]
        assert len(res_export_docx.content) > 5000
        print("[PASS] GET /api/study/export-notes (docx) returned 200 with valid Word stream.")

        # 4f. GET /api/study/download/pdf
        res_pdf_get = client.get("/api/study/download/pdf?topic=Distributed+Consensus&doc_id=syllabus")
        assert res_pdf_get.status_code == 200, res_pdf_get.text
        assert res_pdf_get.headers["content-type"] == "application/pdf"
        assert "attachment; filename=" in res_pdf_get.headers["content-disposition"]
        print("[PASS] GET /api/study/download/pdf returned 200 with direct downloadable stream.")

        # 4g. GET /api/study/download/docx
        res_docx_get = client.get("/api/study/download/docx?topic=Distributed+Consensus&doc_id=syllabus")
        assert res_docx_get.status_code == 200, res_docx_get.text
        assert "openxmlformats" in res_docx_get.headers["content-type"]
        assert "attachment; filename=" in res_docx_get.headers["content-disposition"]
        print("[PASS] GET /api/study/download/docx returned 200 with direct downloadable stream.")

    # Clean up overrides
    app.dependency_overrides.clear()

    print("\n" + "=" * 60)
    print("[ALL TESTS PASSED] Adaptive Study Notes & Downloads Fully Operational!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
