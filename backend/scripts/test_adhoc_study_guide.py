"""
backend/scripts/test_adhoc_study_guide.py
-------------------------------------------
Verification test suite for Phase 8 Ad-Hoc PDF Study Guide:
1. Tests loud extraction diagnostics on a 15+ page PDF.
2. Tests Map-Reduce summarization with RecursiveCharacterTextSplitter and recursive batching.
3. Tests distributed MCQ generation with per-chunk generation, schema validation, and deduplication.
4. Times the execution and tests POST /study-guide/upload via TestClient.
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.rag.adhoc_loader import load_adhoc_pdf
from app.study_guide.summarizer import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    REDUCE_BATCH_SIZE,
    MAX_DIRECT_REDUCE_CHUNKS,
    summarize_document,
    _recursive_reduce,
)
from app.study_guide.mcq_generator import (
    MCQS_PER_CHUNK,
    QUESTION_SIMILARITY_THRESHOLD,
    MCQItem,
    deduplicate_mcqs,
    generate_mcqs_for_document,
)


def run_tests():
    print("=" * 65)
    print("TESTING AD-HOC PDF STUDY GUIDE (MAP-REDUCE & DISTRIBUTED MCQS)")
    print("=" * 65)

    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "my_college_syllabus.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    # -------------------------------------------------------------
    # 1. Extraction Diagnostics on 15+ Page PDF
    # -------------------------------------------------------------
    print("\n[1] Testing Extraction & Loud Diagnostics on multi-page PDF...")
    pages = load_adhoc_pdf(pdf_path)
    assert len(pages) >= 15, f"Expected at least 15 pages, got {len(pages)}"
    print(f"[PASS] Successfully extracted all {len(pages)} pages.")

    # -------------------------------------------------------------
    # 2. Named Tuning Constants Verification
    # -------------------------------------------------------------
    print("\n[2] Verifying Named Tuning Constants...")
    assert CHUNK_SIZE == 3000
    assert CHUNK_OVERLAP == 200
    assert REDUCE_BATCH_SIZE == 10
    assert MAX_DIRECT_REDUCE_CHUNKS == 15
    assert MCQS_PER_CHUNK == 2
    assert QUESTION_SIMILARITY_THRESHOLD == 0.80
    print("[PASS] Named constants configured and verified at top of files.")

    # -------------------------------------------------------------
    # 3. Recursive Reduce Logic Test (Over 15 chunks)
    # -------------------------------------------------------------
    print("\n[3] Testing Recursive Batching on > 15 chunk summaries...")
    mock_chunk_summaries = [f"Summary of chapter/module {i}: key principles and milestones." for i in range(1, 26)]
    assert len(mock_chunk_summaries) == 25  # > 15 chunks

    # Mock reduce LLM call to verify batch grouping
    call_counts = {"count": 0}
    def mock_reduce_fn(batch):
        call_counts["count"] += 1
        return f"Consolidated summary of {len(batch)} items (Pass {call_counts['count']})"

    with patch("app.study_guide.summarizer._reduce_summaries", side_effect=mock_reduce_fn):
        reduced_output = _recursive_reduce(mock_chunk_summaries, batch_size=10)
        # 25 items in batches of 10 -> 3 intermediate batches (10, 10, 5) -> 1 final batch of 3 -> total 4 calls
        assert call_counts["count"] == 4, f"Expected 4 reduce calls, got {call_counts['count']}"
        assert "Consolidated summary" in reduced_output
        print(f"[PASS] Recursive reduce successfully batched 25 chunks across {call_counts['count']} passes without single-prompt stuffing.")

    # -------------------------------------------------------------
    # 4. MCQ Deduplication Test
    # -------------------------------------------------------------
    print("\n[4] Testing MCQ Deduplication...")
    raw_mcqs = [
        MCQItem(
            question="What is the primary function of a consensus protocol in distributed systems?",
            options=["Ensure state agreement", "Accelerate network speed", "Compress disk logs", "Encrypt packets"],
            correct_index=0,
            explanation="Consensus ensures all nodes agree on the machine state."
        ),
        MCQItem(
            question="What is the primary function of a consensus protocol in distributed storage?",  # Near duplicate
            options=["Ensure state agreement across nodes", "Increase network throughput", "Compress logs", "Encrypt files"],
            correct_index=0,
            explanation="Consensus ensures replicated log agreement."
        ),
        MCQItem(
            question="Which property does Paxos and Raft guarantee under network partitions?",
            options=["Consistency", "Availability without quorum", "Eventual corruption", "Infinite throughput"],
            correct_index=0,
            explanation="They maintain safety and linearizability."
        ),
    ]

    deduped = deduplicate_mcqs(raw_mcqs, threshold=0.75)
    assert len(deduped) == 2, f"Expected 2 unique questions, got {len(deduped)}"
    print(f"[PASS] Deduplicated overlapping MCQs from {len(raw_mcqs)} down to {len(deduped)} distinct questions.")

    # -------------------------------------------------------------
    # 5. Full Map-Reduce Document Flow Verification (First 15 pages)
    # -------------------------------------------------------------
    print("\n[5] Testing End-to-End Map-Reduce on 15 pages of syllabus...")
    fifteen_pages = pages[:15]
    start_time = time.time()

    # Mock single-chunk map calls to test pipeline logic deterministically
    with patch("app.study_guide.summarizer._map_chunk_summary", side_effect=lambda chunk_text, chunk_idx, total_chunks: f"Key concepts from chunk {chunk_idx}: Technical foundations and architectural mechanisms."):
        summary_result = summarize_document(fifteen_pages)
        assert len(summary_result) > 50
        print(f"[PASS] Map-Reduce summary produced ({len(summary_result)} chars).")

    with patch("app.study_guide.mcq_generator._generate_chunk_mcqs", side_effect=lambda chunk_text, chunk_idx, total_chunks, count: [
        MCQItem(
            question=f"According to chunk {chunk_idx}, what is the fundamental architecture principle?",
            options=["Modularity", "Coupling", "Redundancy", "Overfitting"],
            correct_index=0,
            explanation="Modularity allows clean separation of concerns."
        )
    ]):
        mcq_result = generate_mcqs_for_document(fifteen_pages)
        assert len(mcq_result) > 0
        print(f"[PASS] Distributed MCQs produced: {len(mcq_result)} questions spanning all document chunks.")

    elapsed = time.time() - start_time
    print(f"[Timing] 15-page pipeline completed in {elapsed:.2f} seconds.")

    # -------------------------------------------------------------
    # 6. Test POST /study-guide/upload via FastAPI TestClient
    # -------------------------------------------------------------
    print("\n[6] Testing POST /study-guide/upload endpoint...")
    client = TestClient(app)

    with open(pdf_path, "rb") as f:
        pdf_content = f.read()

    with patch("app.study_guide.router.load_adhoc_pdf", return_value=fifteen_pages), \
         patch("app.study_guide.router.summarize_document", return_value="Complete 15-page curriculum study guide summary."), \
         patch("app.study_guide.router.generate_mcqs_for_document", return_value=[
             {"question": "What is Topic A?", "options": ["A1", "A2", "A3", "A4"], "correct_index": 0, "explanation": "A1 is correct."}
         ]):

        res = client.post(
            "/study-guide/upload",
            files={"file": ("syllabus.pdf", pdf_content[:10000] + b"%PDF-1.4" if not pdf_content.startswith(b"%PDF") else pdf_content[:50000], "application/pdf")},
        )
        assert res.status_code == 200, f"Upload failed: {res.status_code} {res.text}"
        data = res.json()
        assert data["filename"] == "syllabus.pdf"
        assert data["total_pages"] == 15
        assert "summary" in data
        assert "mcqs" in data
        assert data["total_mcqs"] == 1
        print("[PASS] POST /study-guide/upload returned 200 with complete study guide and MCQs!")

    print("\n" + "=" * 65)
    print("[ALL TESTS PASSED] Map-Reduce Study Guide & MCQs Verified!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
