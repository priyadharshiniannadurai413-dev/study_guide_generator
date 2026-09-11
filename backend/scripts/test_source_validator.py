"""
backend/scripts/test_source_validator.py
----------------------------------------
Unit tests for academic source validation:
- Domain tiering (Tier 1 academic/spec, Tier 2 reference, Blocked social)
- Quality heuristics (length check, error marker detection)
- Combined evidence boundary formatting
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.source_validator import (
    evaluate_domain_tier,
    validate_web_source,
    format_combined_evidence,
)


class TestSourceValidator(unittest.TestCase):

    def test_domain_tiering(self):
        self.assertEqual(evaluate_domain_tier("mit.edu"), "tier_1_academic")
        self.assertEqual(evaluate_domain_tier("cs.stanford.edu"), "tier_1_academic")
        self.assertEqual(evaluate_domain_tier("docs.python.org"), "tier_1_spec")
        self.assertEqual(evaluate_domain_tier("fastapi.tiangolo.com"), "tier_1_spec")
        self.assertEqual(evaluate_domain_tier("en.wikipedia.org"), "tier_2_reference")
        self.assertEqual(evaluate_domain_tier("twitter.com"), "blocked")
        self.assertEqual(evaluate_domain_tier("random-blog.net"), "general_web")

    def test_validate_web_source_rules(self):
        # Short content rejected
        short_res = {
            "status": "success",
            "url": "https://example.com/short",
            "content": "Too short",
            "title": "Short",
        }
        valid, _, reason = validate_web_source(short_res)
        self.assertFalse(valid)
        self.assertIn("too brief", reason.lower())

        # Error marker rejected
        err_res = {
            "status": "success",
            "url": "https://example.com/lost",
            "content": "404 Not Found. The resource you requested could not be located on this server. Please check the URL and try again. This is an automated error message.",
            "title": "Error 404",
        }
        valid, _, reason = validate_web_source(err_res)
        self.assertFalse(valid)
        self.assertIn("error or verification barrier", reason.lower())

        # Valid document accepted
        valid_res = {
            "status": "success",
            "url": "https://docs.python.org/3/library/asyncio.html",
            "content": "# asyncio\nasyncio is a library to write concurrent code using the async/await syntax. " * 5,
            "title": "asyncio — Asynchronous I/O",
        }
        valid, item, _ = validate_web_source(valid_res)
        self.assertTrue(valid)
        self.assertEqual(item.get("tier"), "tier_1_spec")
        self.assertEqual(item.get("title"), "asyncio — Asynchronous I/O")

    def test_format_combined_evidence_boundaries(self):
        rag_chunks = [
            {"doc_id": "syllabus_unit_1", "page_number": 3, "text": "Operating System Kernels and Processes."}
        ]
        web_sources = [
            {"title": "Linux Kernel Docs", "url": "https://kernel.org", "tier": "tier_1_spec", "content": "Monolithic vs Microkernel architectures."}
        ]
        combined = format_combined_evidence(rag_chunks, web_sources)
        self.assertIn("=== UPLOADED DOCUMENT EVIDENCE ===", combined)
        self.assertIn("[Doc Chunk 1 | Source: syllabus_unit_1 | Page 3]", combined)
        self.assertIn("=== EXTERNAL WEB EVIDENCE (FETCH MCP) ===", combined)
        self.assertIn("[Web Source 1 | Linux Kernel Docs | Quality: tier_1_spec]", combined)


if __name__ == "__main__":
    unittest.main()
