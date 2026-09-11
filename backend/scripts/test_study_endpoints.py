from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user

# Override auth dependency for tests
async def mock_current_user():
    return {"sub": "test_student_user_123", "email": "student@college.edu"}

app.dependency_overrides[get_current_user] = mock_current_user

client = TestClient(app)

def test_endpoints():
    print("==================================================")
    print("TESTING FASTAPI STUDY & EXPORT ENDPOINTS")
    print("==================================================")

    # 1. Test /api/study/topic-notes
    print("\n[1] Testing POST /api/study/topic-notes...")
    resp = client.post(
        "/api/study/topic-notes",
        json={"topic": "Pointers in C", "doc_id": "syllabus"},
    )
    print(f"Status Code: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    print(f"Returned topic: {data.get('topic_title')}")
    print(f"Concepts returned: {len(data.get('concepts', []))}")
    assert "concepts" in data and len(data["concepts"]) > 0
    assert "key_takeaways" in data and len(data["key_takeaways"]) > 0
    assert "common_pitfalls" in data and len(data["common_pitfalls"]) > 0
    print("[PASS] /api/study/topic-notes returned valid TopicStudyNotes JSON.")

    # 2. Test /api/study/export/pdf with pre-generated notes
    print("\n[2] Testing POST /api/study/export/pdf with payload...")
    pdf_resp = client.post(
        "/api/study/export/pdf",
        json={"notes": data},
    )
    print(f"Status Code: {pdf_resp.status_code}")
    print(f"Content-Type: {pdf_resp.headers.get('content-type')}")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers.get("content-type") == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-")
    print(f"PDF bytes size: {len(pdf_resp.content)} bytes")
    print("[PASS] /api/study/export/pdf returned valid application/pdf buffer.")

    # 3. Test /api/study/export/docx with pre-generated notes
    print("\n[3] Testing POST /api/study/export/docx with payload...")
    docx_resp = client.post(
        "/api/study/export/docx",
        json={"notes": data},
    )
    print(f"Status Code: {docx_resp.status_code}")
    print(f"Content-Type: {docx_resp.headers.get('content-type')}")
    assert docx_resp.status_code == 200
    assert "officedocument.wordprocessingml.document" in docx_resp.headers.get("content-type")
    assert docx_resp.content.startswith(b"PK\x03\x04")
    print(f"DOCX bytes size: {len(docx_resp.content)} bytes")
    print("[PASS] /api/study/export/docx returned valid Word document buffer.")

    print("\n==================================================")
    print("[ALL ENDPOINT CHECKS PASSED] FastAPI Routes Verified!")
    print("==================================================")

if __name__ == "__main__":
    test_endpoints()
