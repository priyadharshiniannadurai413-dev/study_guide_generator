"""
scripts/test_export_notes_endpoint.py
-------------------------------------
Verifies that GET /api/study/export-notes returns a clean, publication-ready PDF stream
with the exact headers required for the one-click download feature.
"""

import io
import os
import sys
import pypdf
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.auth.dependencies import get_current_user

def test_export_notes_endpoint():
    print("=" * 65)
    print("TESTING GET /api/study/export-notes ENDPOINT")
    print("=" * 65)

    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test_student_user",
        "email": "student@college.edu",
    }
    client = TestClient(app)

    # Call GET /api/study/export-notes
    resp = client.get("/api/study/export-notes", params={
        "topic": "Distributed Consensus & Raft",
        "file_format": "pdf",
    })

    print(f"Status Code: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}")
    print(f"Content-Disposition: {resp.headers.get('content-disposition')}")
    print(f"Access-Control-Expose-Headers: {resp.headers.get('access-control-expose-headers')}")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "application/pdf" in resp.headers.get("content-type", ""), "Media type must be application/pdf"
    assert "attachment;" in resp.headers.get("content-disposition", ""), "Must have attachment header"
    assert "Content-Disposition" in resp.headers.get("access-control-expose-headers", ""), "Must expose Content-Disposition"

    pdf_bytes = resp.content
    print(f"Downloaded PDF size: {len(pdf_bytes):,} bytes")
    assert len(pdf_bytes) > 1000, "PDF size must be non-empty"

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    print(f"Generated PDF Page Count: {len(reader.pages)}")
    assert len(reader.pages) >= 1, "PDF must have at least 1 page"

    first_page_text = reader.pages[0].extract_text()
    print("Sample PDF Text:\n", first_page_text[:400])
    assert "Distributed Consensus" in first_page_text or "Executive Summary" in first_page_text, "PDF must contain substantive topic text"

    print("=" * 65)
    print("[PASS] GET /api/study/export-notes verified successfully!")
    print("=" * 65)

if __name__ == "__main__":
    test_export_notes_endpoint()
