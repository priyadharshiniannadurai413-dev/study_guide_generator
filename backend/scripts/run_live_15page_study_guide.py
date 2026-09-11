"""
backend/scripts/run_live_15page_study_guide.py
------------------------------------------------
Live verification script running Map-Reduce summarization and MCQ generation
against 15 real pages of uploads/my_college_syllabus.pdf.
Measures real LLM execution time and verifies cross-document coverage.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.rag.adhoc_loader import load_adhoc_pdf
from app.study_guide.summarizer import summarize_document
from app.study_guide.mcq_generator import generate_mcqs_for_document


def run_live_test():
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "my_college_syllabus.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    print("=" * 65)
    print("LIVE MULTI-PAGE (15 PAGES) STUDY GUIDE & MCQ VERIFICATION")
    print("=" * 65)

    pages = load_adhoc_pdf(pdf_path)
    sample_pages = pages[:15]
    print(f"Loaded {len(sample_pages)} pages from {os.path.basename(pdf_path)}.")
    total_chars = sum(len(p.get("text", "")) for p in sample_pages)
    print(f"Total characters across 15 pages: {total_chars:,} chars.")

    # 1. Summarization timing & verification
    print("\n--- Running Map-Reduce Summarization ---")
    start_sum = time.time()
    summary = summarize_document(sample_pages, chunk_size=3000, chunk_overlap=200)
    sum_time = time.time() - start_sum
    print(f"\n[Summary Result ({len(summary)} chars, generated in {sum_time:.2f}s)]:")
    print("-" * 50)
    print(summary[:1200] + ("\n... [truncated for display] ...\n" if len(summary) > 1200 else ""))
    print("-" * 50)

    # 2. MCQ generation timing & verification
    print("\n--- Running Distributed MCQ Generation ---")
    start_mcq = time.time()
    mcqs = generate_mcqs_for_document(sample_pages, chunk_size=3000, chunk_overlap=200, mcqs_per_chunk=2)
    mcq_time = time.time() - start_mcq
    print(f"\n[MCQ Result ({len(mcqs)} questions, generated in {mcq_time:.2f}s)]:")
    for idx, q in enumerate(mcqs[:4], start=1):
        print(f"\nQ{idx}: {q['question']}")
        for opt_idx, opt in enumerate(q['options']):
            marker = "*" if opt_idx == q['correct_index'] else " "
            print(f"   [{marker}] {chr(65 + opt_idx)}. {opt}")
        print(f"   Explanation: {q['explanation'][:120]}...")

    total_time = sum_time + mcq_time
    print("\n" + "=" * 65)
    print(f"TOTAL EXECUTION TIME: {total_time:.2f} seconds (Summarization: {sum_time:.2f}s, MCQs: {mcq_time:.2f}s)")
    if total_time > 30:
        print("[NOTICE] Pipeline took > 30 seconds due to sequential per-chunk LLM calls.")
        print("Async parallelization with asyncio.gather is recommended as follow-up.")
    else:
        print("[PERFORMANCE] Execution completed under 30 seconds.")
    print("=" * 65)


if __name__ == "__main__":
    run_live_test()
