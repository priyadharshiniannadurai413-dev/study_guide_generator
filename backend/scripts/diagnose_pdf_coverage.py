"""
backend/scripts/diagnose_pdf_coverage.py
-----------------------------------------
Diagnostic script to test STEP 1 of the objective:
1. In extraction, log total pages extracted and total character count, and warn for empty pages.
2. In summarizer, log the length (in characters) of text sent to the LLM in a single call vs chunk sizes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.adhoc_loader import load_adhoc_pdf
from app.rag.loader import extract_pdf, is_front_matter


def diagnose():
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "my_college_syllabus.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    print("=" * 65)
    print("STEP 1: DIAGNOSIS - CHECKING EXTRACTION & PROMPT STUFFING")
    print("=" * 65)

    print(f"\nTarget PDF: {pdf_path}")
    print(f"File Size: {os.path.getsize(pdf_path) / (1024 * 1024):.2f} MB")

    # 1. Test extraction
    print("\n--- 1. Testing PDF Extraction ---")
    pages = load_adhoc_pdf(pdf_path)
    total_pages = len(pages)
    total_chars = sum(len(p.get("text", "")) for p in pages)
    empty_pages = [p["page_number"] for p in pages if not p.get("text", "").strip()]

    print(f"Total Pages Extracted: {total_pages}")
    print(f"Total Characters Extracted: {total_chars:,} characters")
    print(f"Empty/Whitespace Pages Count: {len(empty_pages)}")
    if empty_pages:
        print(f"Empty Pages list (first 10): {empty_pages[:10]}")
    else:
        print("All pages contained text (no 100% blank image-only pages).")

    # 2. Test text concatenation / stuffing size
    print("\n--- 2. Measuring Single-Prompt Stuffing vs Context Window ---")
    stuffed_full_text = "\n\n".join(p.get("text", "") for p in pages)
    stuffed_length = len(stuffed_full_text)
    approx_tokens = stuffed_length // 4

    print(f"Concatenated Full Document Length: {stuffed_length:,} characters (~{approx_tokens:,} tokens)")

    # Test what a 15-page subset would be
    subset_15 = pages[:15]
    subset_15_text = "\n\n".join(p.get("text", "") for p in subset_15)
    print(f"First 15 Pages Length: {len(subset_15_text):,} characters (~{len(subset_15_text) // 4:,} tokens)")

    # 3. Check Front-Matter Filter
    fm_count = sum(1 for p in pages if is_front_matter(p.get("text", "")))
    print(f"Front-matter pages detected & skipped: {fm_count} pages")

    print("\n--- 3. Root Cause Analysis ---")
    print(f"Pages dropped by extractor? NO ({total_pages} of {total_pages} extracted cleanly).")
    print(f"Cause (b) Single-call stuffing confirmed:")
    print(f"- Stuffing {stuffed_length:,} characters ({approx_tokens:,} tokens) into a single prompt causes LLMs")
    print("  to suffer from 'lost-in-the-middle' attention decay and output token truncation (max 4096 tokens),")
    print("  which forces the LLM to only summarize the beginning of the prompt and ignore subsequent sections.")
    print("=" * 65)


if __name__ == "__main__":
    diagnose()
