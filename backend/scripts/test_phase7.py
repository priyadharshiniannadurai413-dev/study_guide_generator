"""
scripts/test_phase7.py
----------------------
End-to-end integration test suite for Phase 7:
1. Health check (/health)
2. Authentication protection on protected endpoints
3. User PDF upload (/api/documents/upload)
4. Dedicated study generation (/api/study/mcq, /api/study/notes)
5. SSE streaming chat (/api/chat/stream)
6. Voice speech synthesis (/api/voice/synthesize)
7. Cleanup of test documents
"""

import asyncio
import io
import json
import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from app.auth.dependencies import get_current_user
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_user_doc_collection
from app.main import app


def create_sample_pdf_bytes() -> bytes:
    """Minimal valid PDF containing academic engineering text."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 260 >> stream\n"
        b"BT /F1 12 Tf 50 720 Td (Operational Amplifiers Op-Amps: Inverting and Non-Inverting configurations.) Tj\n"
        b"0 -20 Td (An ideal op-amp has infinite input impedance, zero output impedance, and infinite open-loop gain.) Tj\n"
        b"0 -20 Td (Closed-loop voltage gain for inverting amplifier is Av = -Rf / Rin.) Tj\n"
        b"0 -20 Td (Virtual ground concept arises from infinite open-loop gain where V+ equals V-.) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000556 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"627\n"
        b"%%EOF\n"
    )


async def run_tests():
    print("=" * 65)
    print("PHASE 7 INTEGRATION & POLISH TEST SUITE")
    print("=" * 65)

    await connect_to_mongo()

    test_user_id = "student_test_phase7_user"
    test_pdf_bytes = create_sample_pdf_bytes()
    doc_id = None

    async def mock_current_user():
        return {
            "sub": test_user_id,
            "email": "test_phase7@example.com",
            "name": "Test Student",
        }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=45.0) as client:
        # 1. Health check
        print("\n[1] Testing /health endpoint...")
        resp_health = await client.get("/health")
        assert resp_health.status_code == 200, f"Health check failed: {resp_health.status_code}"
        assert resp_health.json().get("status") == "ok"
        print("  [PASS] /health returned status: ok")

        # 2. Verify Authentication Guards
        print("\n[2] Verifying authentication protection on private endpoints...")
        resp_unauth_chat = await client.post("/api/chat/stream", json={"user_prompt": "Hello"})
        assert resp_unauth_chat.status_code == 401, f"Expected 401, got {resp_unauth_chat.status_code}"

        resp_unauth_mcq = await client.post("/api/study/mcq", json={"doc_id": "dummy"})
        assert resp_unauth_mcq.status_code == 401, f"Expected 401, got {resp_unauth_mcq.status_code}"

        resp_unauth_notes = await client.post("/api/study/notes", json={"doc_id": "dummy"})
        assert resp_unauth_notes.status_code == 401, f"Expected 401, got {resp_unauth_notes.status_code}"
        print("  [PASS] All protected endpoints rejected unauthenticated requests with HTTP 401.")

        # Enable dependency override for authenticated tests
        app.dependency_overrides[get_current_user] = mock_current_user

        # 3. Document Upload
        print("\n[3] Testing /api/documents/upload with test PDF...")
        files = {"file": ("op_amps_lecture.pdf", test_pdf_bytes, "application/pdf")}
        resp_upload = await client.post("/api/documents/upload", files=files)
        assert resp_upload.status_code == 201, f"Upload failed: {resp_upload.status_code} {resp_upload.text}"
        upload_data = resp_upload.json()
        doc_id = upload_data["doc_id"]
        print(f"  [PASS] Ingested document: doc_id={doc_id}, chunks={upload_data['total_chunks']}")

        # 4. Dedicated Study Endpoints: MCQ Quiz Generation
        print(f"\n[4] Testing /api/study/mcq for doc_id={doc_id}...")
        resp_mcq = await client.post("/api/study/mcq", json={"doc_id": doc_id, "count": 3})
        assert resp_mcq.status_code == 200, f"MCQ generation failed: {resp_mcq.status_code} {resp_mcq.text}"
        quiz_data = resp_mcq.json()
        questions = quiz_data.get("questions", [])
        print(f"  Generated {len(questions)} MCQs under title: '{quiz_data.get('title')}'")
        assert len(questions) >= 1, "Expected at least 1 question"

        for idx, q in enumerate(questions, 1):
            assert len(q["options"]) == 4, f"Question {idx} does not have 4 options: {len(q['options'])}"
            assert 0 <= q["correct_index"] <= 3, f"Question {idx} correct_index out of range: {q['correct_index']}"
            assert len(q["explanation"]) > 0, f"Question {idx} missing explanation"
            print(f"  [PASS] Question {idx}: {q['question'][:65]}... (Answer option: {q['correct_index']})")

        # 5. Dedicated Study Endpoints: High-Yield Notes Generation
        print(f"\n[5] Testing /api/study/notes for doc_id={doc_id}...")
        resp_notes = await client.post("/api/study/notes", json={"doc_id": doc_id})
        assert resp_notes.status_code == 200, f"Study notes generation failed: {resp_notes.status_code} {resp_notes.text}"
        notes_data = resp_notes.json()
        assert "executive_summary" in notes_data and len(notes_data["executive_summary"]) > 0
        assert "key_concepts" in notes_data and len(notes_data["key_concepts"]) > 0
        print(f"  [PASS] Study notes executive summary: {notes_data['executive_summary'][:75]}...")
        print(f"  [PASS] Key concepts identified: {len(notes_data['key_concepts'])} concepts")

        # 6. SSE Streaming Chat (/api/chat/stream)
        print("\n[6] Testing /api/chat/stream with real-time SSE token delivery...")
        stream_payload = {
            "user_prompt": "What is the closed-loop voltage gain formula for an inverting amplifier?",
        }
        tokens_received = []
        async with client.stream("POST", "/api/chat/stream", json=stream_payload) as stream_resp:
            assert stream_resp.status_code == 200, f"Streaming failed: {stream_resp.status_code}"
            assert "text/event-stream" in stream_resp.headers.get("content-type", "")

            async for line in stream_resp.aiter_lines():
                if not line or not line.strip():
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        parsed = json.loads(data_str)
                        if "text" in parsed:
                            tokens_received.append(parsed["text"])
                    except Exception:
                        tokens_received.append(data_str)

        full_stream_text = "".join(tokens_received)
        print(f"  Tokens streamed: {len(tokens_received)} chunks ({len(full_stream_text)} chars)")
        print(f"  Stream preview: {full_stream_text[:120]}...")
        assert len(full_stream_text) > 0, "No content received from stream"
        print("  [PASS] Live SSE streaming chat verified successfully.")

        # 7. Voice TTS Synthesis (/api/voice/synthesize)
        print("\n[7] Testing /api/voice/synthesize MP3 audio generation...")
        resp_voice = await client.post("/api/voice/synthesize", json={"text": "Welcome to the AI Study Assistant."})
        assert resp_voice.status_code == 200, f"Voice synthesis failed: {resp_voice.status_code}"
        assert "audio/mpeg" in resp_voice.headers.get("content-type", "")
        audio_content = resp_voice.content
        print(f"  Received MP3 audio buffer: {len(audio_content)} bytes")
        assert len(audio_content) > 100, "Audio content buffer too small"
        print("  [PASS] Edge-TTS audio stream generated and returned successfully.")

        # 8. Cleanup uploaded test document
        print("\n[8] Cleaning up test document...")
        resp_del = await client.delete(f"/api/documents/{doc_id}")
        assert resp_del.status_code == 200, f"Cleanup failed: {resp_del.status_code}"
        print("  [PASS] Test document deleted.")

    # Reset dependency overrides & close DB
    app.dependency_overrides.clear()
    await close_mongo_connection()

    print("\n" + "=" * 65)
    print("ALL PHASE 7 INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_tests())
