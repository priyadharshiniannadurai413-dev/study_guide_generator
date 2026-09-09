"""
scripts/test_phase5.py
----------------------
Comprehensive verification test suite for Phase 5:
1. Generates a valid test PDF with academic notes.
2. Ingests via process_user_pdf for user_A.
3. Asserts user_id, doc_id, and embeddings are correctly stored in user_documents.
4. Asserts get_user_doc_context retrieves relevant chunks for user_A.
5. Asserts get_user_doc_context returns 0 chunks for user_B (strict cross-user tenant isolation).
6. Verifies FastAPI /api/documents endpoints (auth protection, list, cross-user delete prevention).
7. Verifies global syllabus collection (vector_documents) remains completely untouched.
"""

import asyncio
import io
import os
import sys

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.auth.dependencies import get_current_user
from app.db.mongodb import (
    close_mongo_connection,
    connect_to_mongo,
    get_user_doc_collection,
    get_vector_collection,
)
from app.main import app
from app.rag.user_doc_retriever import get_user_doc_context
from app.rag.user_doc_service import process_user_pdf


def create_sample_pdf_bytes() -> bytes:
    """Create an in-memory PDF with academic text using pypdf."""
    from pypdf import PageObject

    # Note: pypdf can create a blank page or we can use a minimal PDF byte stream
    # A standard minimal 1-page PDF:
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 215 >> stream\n"
        b"BT /F1 12 Tf 50 720 Td (Digital Signal Processing: Fast Fourier Transform FFT and Cooley-Tukey algorithm.) Tj\n"
        b"0 -20 Td (Decimation-in-time DIT algorithm decomposes an N-point DFT into two N/2 point DFTs.) Tj\n"
        b"0 -20 Td (Computational complexity is reduced from O(N^2) to O(N log N).) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000511 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"582\n"
        b"%%EOF\n"
    )
    return pdf_content


async def run_tests():
    print("=" * 60)
    print("PHASE 5 VERIFICATION TEST SUITE")
    print("=" * 60)

    await connect_to_mongo()

    user_A = "user_student_alpha_101"
    user_B = "user_student_beta_202"
    filename = "DSP_FFT_Lecture_Notes.pdf"
    pdf_bytes = create_sample_pdf_bytes()

    # Baseline: Check syllabus collection chunk count
    syllabus_coll = get_vector_collection()
    initial_syllabus_count = await syllabus_coll.count_documents({})
    print(f"\n[Baseline] Syllabus vector_documents count: {initial_syllabus_count}")

    # 1. Ingest PDF for user_A
    print("\n[1] Ingesting PDF via process_user_pdf for user_A...")
    result = await process_user_pdf(pdf_bytes, filename, user_A)
    doc_id = result["doc_id"]
    print(f"  Ingested doc_id: {doc_id}")
    print(f"  Total chunks: {result['total_chunks']}")
    assert result["total_chunks"] >= 1, "Expected at least 1 chunk generated"

    # 2. Verify MongoDB storage & metadata
    print("\n[2] Verifying user_documents collection in MongoDB...")
    user_coll = get_user_doc_collection()
    chunks = await user_coll.find({"doc_id": doc_id}).to_list(length=100)
    print(f"  Chunks found in MongoDB: {len(chunks)}")
    assert len(chunks) == result["total_chunks"]

    for c in chunks:
        assert c["user_id"] == user_A, f"Chunk user_id mismatch: {c['user_id']}"
        assert c["doc_id"] == doc_id, f"Chunk doc_id mismatch: {c['doc_id']}"
        assert c["filename"] == filename
        assert "embedding" in c and len(c["embedding"]) == 384, "Embedding missing or dimension mismatch"
        print(f"  [PASS] Chunk {c['chunk_id']} verified: user_id={c['user_id']}, emb_len={len(c['embedding'])}")

    # 3. Test Retrieval for user_A (Authorized)
    print("\n[3] Testing retrieval for owner user_A...")
    chunks_A = await get_user_doc_context(user_A, doc_id, "Explain Fast Fourier Transform complexity", top_k=3)
    print(f"  Retrieved {len(chunks_A)} chunks for user_A")
    assert len(chunks_A) > 0, "user_A should retrieve chunks"
    print(f"  Top chunk preview: {chunks_A[0]['text'][:80]}... (score: {chunks_A[0].get('score')})")
    print("  [PASS] Authorized retrieval successful.")

    # 4. Test Cross-User Isolation (Mismatched user_B)
    print("\n[4] Testing cross-user isolation for unauthorized user_B...")
    chunks_B = await get_user_doc_context(user_B, doc_id, "Explain Fast Fourier Transform complexity", top_k=3)
    print(f"  Retrieved {len(chunks_B)} chunks for user_B")
    assert len(chunks_B) == 0, f"SECURITY VIOLATION: user_B retrieved {len(chunks_B)} chunks belonging to user_A!"
    print("  [PASS] Strict cross-user isolation confirmed: 0 chunks returned for unauthorized user.")

    # 5. Verify syllabus collection was NOT touched
    final_syllabus_count = await syllabus_coll.count_documents({})
    assert final_syllabus_count == initial_syllabus_count, "Global syllabus collection was polluted!"
    print(f"\n[5] Global syllabus collection unchanged: {final_syllabus_count} chunks.")

    # 6. Test FastAPI endpoints via httpx.AsyncClient
    print("\n[6] Testing FastAPI routes (/api/documents/*)...")
    import httpx

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 6a. Unauthorized access without auth header -> 401
        resp_unauth = await client.get("/api/documents/")
        assert resp_unauth.status_code == 401, f"Expected 401, got {resp_unauth.status_code}"
        print("  [PASS] GET /api/documents/ protected: HTTP 401")

        # 6b. Test list with mocked user_A
        async def mock_get_user_A():
            return {"sub": user_A, "email": "studentA@example.com"}

        async def mock_get_user_B():
            return {"sub": user_B, "email": "studentB@example.com"}

        app.dependency_overrides[get_current_user] = mock_get_user_A
        resp_list = await client.get("/api/documents/")
        assert resp_list.status_code == 200, f"List failed: {resp_list.status_code}"
        doc_list = resp_list.json()
        print(f"  User A doc list: {[d['doc_id'] for d in doc_list]}")
        assert any(d["doc_id"] == doc_id for d in doc_list), "Ingested doc not found in user A list"
        print("  [PASS] GET /api/documents/ returned user A's document catalog.")

        # 6c. Test cross-user delete prevention (user_B trying to delete user_A's doc)
        app.dependency_overrides[get_current_user] = mock_get_user_B
        resp_del_unauth = await client.delete(f"/api/documents/{doc_id}")
        assert resp_del_unauth.status_code == 404, f"Expected 404 on cross-user delete, got {resp_del_unauth.status_code}"
        print("  [PASS] Cross-user deletion prevented: HTTP 404 returned for user_B.")

        # 6d. Test delete with owner user_A
        app.dependency_overrides[get_current_user] = mock_get_user_A
        resp_del = await client.delete(f"/api/documents/{doc_id}")
        assert resp_del.status_code == 200, f"Delete failed: {resp_del.status_code}"
        print(f"  Delete response: {resp_del.json()}")

    # Verify chunks purged from MongoDB
    remaining = await user_coll.count_documents({"doc_id": doc_id})
    assert remaining == 0, f"Chunks still present after deletion: {remaining}"
    print("  [PASS] Document chunks successfully purged from user_documents.")

    # Clean up overrides & close connection
    app.dependency_overrides.clear()
    await close_mongo_connection()

    print("\n" + "=" * 60)
    print("ALL PHASE 5 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
