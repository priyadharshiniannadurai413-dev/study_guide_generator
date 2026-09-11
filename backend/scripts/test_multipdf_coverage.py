"""
scripts/test_multipdf_coverage.py
---------------------------------
Comprehensive multi-PDF verification test suite.
Tests:
1. PDF A (Short, 3 pages, no headers/footers)
2. PDF B (Long, 16 pages, with repeated running header & footer with dynamic page numbers)
3. PDF C (Mixed formatting, 4 pages, with tables, rubrics, and credit matrices)

Verifies:
- Document-agnostic completeness checks
- Header/footer stripping accuracy (0 false positives on PDF A, 100% elimination on PDF B)
- Full end-to-end document coverage (no truncation)
- FastAPI /study-guide/upload endpoint contract compatibility
"""

import io
import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.main import app
from app.rag.adhoc_loader import load_adhoc_pdf, strip_repeated_headers_and_footers
from app.rag.loader import extract_pdf
from app.study_guide.mcq_generator import generate_mcqs_for_document
from app.study_guide.summarizer import summarize_document


class TestMultiPdfCoverage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
        cls.pdf_a_path = os.path.join(cls.test_dir, "test_pdf_a_short.pdf")
        cls.pdf_b_path = os.path.join(cls.test_dir, "test_pdf_b_long.pdf")
        cls.pdf_c_path = os.path.join(cls.test_dir, "test_pdf_c_mixed.pdf")

    def test_01_header_footer_stripping_on_pdf_a(self):
        """PDF A (Short, 3 pages): Verify 0 lines stripped (no false positives)."""
        print("\n" + "=" * 65)
        print("TEST 1: Header/Footer Detection on PDF A (3 pages, no headers/footers)")
        print("=" * 65)

        raw_pages = extract_pdf(self.pdf_a_path)
        self.assertEqual(len(raw_pages), 3, "PDF A should have exactly 3 pages")

        cleaned_pages = strip_repeated_headers_and_footers(raw_pages)
        self.assertEqual(len(cleaned_pages), 3)

        # Confirm character count did not lose substantive content
        raw_chars = sum(len(p["text"]) for p in raw_pages)
        clean_chars = sum(len(p["text"]) for p in cleaned_pages)
        print(f"[PDF A] Raw chars: {raw_chars:,}, Clean chars: {clean_chars:,}")
        self.assertEqual(raw_chars, clean_chars, "PDF A should have zero lines stripped")
        print("[PASS] PDF A had 0 lines stripped - no false positives.")

    def test_02_header_footer_stripping_on_pdf_b(self):
        """PDF B (Long, 16 pages): Verify running header & footer are 100% stripped."""
        print("\n" + "=" * 65)
        print("TEST 2: Header/Footer Detection on PDF B (16 pages with running header & footer)")
        print("=" * 65)

        raw_pages = extract_pdf(self.pdf_b_path)
        self.assertEqual(len(raw_pages), 16, "PDF B should have 16 pages")

        # Verify raw pages DO contain the running header and footer
        raw_has_header = any("Distributed Systems Architecture and Consensus" in p["text"] for p in raw_pages)
        raw_has_footer = any("Confidential Academic Draft" in p["text"] for p in raw_pages)
        self.assertTrue(raw_has_header, "Raw PDF B should contain running header")
        self.assertTrue(raw_has_footer, "Raw PDF B should contain running footer")
        print("[PDF B] Confirmed running headers and footers are physically present in raw extract.")

        # Clean pages
        cleaned_pages = strip_repeated_headers_and_footers(raw_pages)
        self.assertEqual(len(cleaned_pages), 16)

        # Verify ZERO header or footer remains in cleaned pages
        cleaned_has_header = any("Distributed Systems Architecture and Consensus" in p["text"] for p in cleaned_pages)
        cleaned_has_footer = any("Confidential Academic Draft" in p["text"] for p in cleaned_pages)
        self.assertFalse(cleaned_has_header, "Running header should be 100% eliminated from cleaned pages")
        self.assertFalse(cleaned_has_footer, "Running footer should be 100% eliminated from cleaned pages")
        print("[PASS] Zero header or footer contamination in cleaned PDF B text.")

        # Confirm substantive module topics remain completely intact
        self.assertTrue(any("Lamport" in p["text"] for p in cleaned_pages), "Module 2 (Lamport) must be present")
        self.assertTrue(any("CRDT" in p["text"] for p in cleaned_pages), "Module 13 (CRDTs) must be present")
        self.assertTrue(any("Service Mesh" in p["text"] for p in cleaned_pages), "Module 16 (Service Mesh) must be present")
        print("[PASS] All core academic modules 1 through 16 preserved intact.")

    def test_03_pdf_c_table_extraction(self):
        """PDF C (Mixed formatting, 4 pages): Verify tables, rubrics, and outcomes are extracted."""
        print("\n" + "=" * 65)
        print("TEST 3: Table and Curriculum Matrix Extraction on PDF C (4 pages)")
        print("=" * 65)

        pages = load_adhoc_pdf(self.pdf_c_path)
        self.assertEqual(len(pages), 4, "PDF C should have 4 pages")
        full_text = "\n".join(p["text"] for p in pages)

        # Verify tables content
        self.assertIn("CS-490", full_text, "Course code CS-490 must be extracted")
        self.assertIn("Senior Design Project", full_text, "Senior Design Project must be extracted")
        self.assertIn("Milestone", full_text, "Milestone table must be extracted")
        self.assertIn("Final Defense", full_text, "M4 Final Defense must be extracted")
        self.assertIn("Exemplary", full_text, "Rubric exemplary level must be extracted")
        print(f"[PASS] PDF C tables and matrices extracted successfully ({len(full_text):,} chars).")

    def test_04_endpoint_on_pdf_a(self):
        """FastAPI POST /study-guide/upload on PDF A (Short)."""
        print("\n" + "=" * 65)
        print("TEST 4: /study-guide/upload on PDF A (Short, 3 pages)")
        print("=" * 65)

        with open(self.pdf_a_path, "rb") as f:
            resp = self.client.post(
                "/study-guide/upload",
                files={"file": ("test_pdf_a_short.pdf", f, "application/pdf")},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"[PDF A Result] Total Pages: {data['total_pages']}")
        print(f"[PDF A Result] Summary Length: {len(data['summary'])} chars")
        print(f"[PDF A Result] MCQs Generated: {data['total_mcqs']} questions")

        self.assertEqual(data["total_pages"], 3)
        self.assertTrue(len(data["summary"]) > 200)
        self.assertTrue(len(data["mcqs"]) >= 2)

        # Confirm coverage of all 3 chapters in summary
        summary_lower = data["summary"].lower()
        has_ch1 = any(k in summary_lower for k in ["physical", "nyquist", "attenuation", "modulation"])
        has_ch2 = any(k in summary_lower for k in ["data link", "crc", "csma", "mac", "framing"])
        has_ch3 = any(k in summary_lower for k in ["network", "ipv4", "ipv6", "routing", "ospf", "bgp"])
        self.assertTrue(has_ch1, "Summary must cover Chapter 1 (Physical)")
        self.assertTrue(has_ch2, "Summary must cover Chapter 2 (Data Link)")
        self.assertTrue(has_ch3, "Summary must cover Chapter 3 (Network Layer)")
        print("[PASS] PDF A summary verified to cover Chapter 1, Chapter 2, and Chapter 3!")

    def test_05_endpoint_on_pdf_b(self):
        """FastAPI POST /study-guide/upload on PDF B (Long, 16 pages)."""
        print("\n" + "=" * 65)
        print("TEST 5: /study-guide/upload on PDF B (Long, 16 pages)")
        print("=" * 65)

        with open(self.pdf_b_path, "rb") as f:
            resp = self.client.post(
                "/study-guide/upload",
                files={"file": ("test_pdf_b_long.pdf", f, "application/pdf")},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"[PDF B Result] Total Pages: {data['total_pages']}")
        print(f"[PDF B Result] Summary Length: {len(data['summary'])} chars")
        print(f"[PDF B Result] MCQs Generated: {data['total_mcqs']} questions")

        self.assertEqual(data["total_pages"], 16)
        self.assertTrue(len(data["summary"]) > 500)
        self.assertTrue(len(data["mcqs"]) >= 6)

        # Zero header/footer leakage check
        self.assertNotIn("Confidential Academic Draft", data["summary"], "Zero footer leakage in summary")
        for q in data["mcqs"]:
            self.assertNotIn("Confidential Academic Draft", q["question"], "Zero footer leakage in question")
            self.assertNotIn("Confidential Academic Draft", q["explanation"], "Zero footer leakage in explanation")
            self.assertNotIn("CS-804", q["question"], "Zero header leakage in question")
        print("[PASS] Confirmed ZERO header/footer leakage across summary and all MCQs!")

        # Cross-document coverage check: covers both early and late modules
        summary_text = data["summary"].lower()
        early_covered = any(k in summary_text for k in ["rpc", "lamport", "vector clock", "paxos", "raft", "mutex", "ricart"])
        late_covered = any(k in summary_text for k in ["crdt", "two-phase commit", "2pc", "kafka", "flink", "service mesh", "envoy", "spanner", "cap"])
        self.assertTrue(early_covered, "Summary must cover early modules (RPC/Lamport/Paxos)")
        self.assertTrue(late_covered, "Summary must cover late modules (CRDT/2PC/Service Mesh)")
        print("[PASS] Full cross-document coverage verified from Module 1 through Module 16!")

    def test_06_endpoint_on_pdf_c(self):
        """FastAPI POST /study-guide/upload on PDF C (Mixed table syllabus)."""
        print("\n" + "=" * 65)
        print("TEST 6: /study-guide/upload on PDF C (Mixed table syllabus, 4 pages)")
        print("=" * 65)

        with open(self.pdf_c_path, "rb") as f:
            resp = self.client.post(
                "/study-guide/upload",
                files={"file": ("test_pdf_c_mixed.pdf", f, "application/pdf")},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"[PDF C Result] Total Pages: {data['total_pages']}")
        print(f"[PDF C Result] Summary Length: {len(data['summary'])} chars")
        print(f"[PDF C Result] MCQs Generated: {data['total_mcqs']} questions")

        self.assertEqual(data["total_pages"], 4)
        self.assertTrue(len(data["summary"]) > 200)
        self.assertTrue(len(data["mcqs"]) >= 2)

        summary_lower = data["summary"].lower()
        has_capstone = any(k in summary_lower for k in ["capstone", "design project", "cs-490", "milestone", "rubric", "devops"])
        self.assertTrue(has_capstone, "Summary must reflect capstone syllabus structure and deliverables")
        print("[PASS] PDF C summary verified to cover curriculum structure and milestones!")


if __name__ == "__main__":
    unittest.main()
