"""
backend/scripts/test_web_content_service.py
-------------------------------------------
Comprehensive unit and integration test suite for:
- Conservative boilerplate removal & Wikipedia cleanup
- WebDocumentModel structure
- Large webpage chunking & relevance ranking
- Grounded Q&A generation with honest "not enough information" fallback
- FastAPI /api/web/fetch and /api/web/ask endpoints
"""

import asyncio
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.web_content_service import (
    WebDocumentModel,
    WebContentService,
    clean_markdown_content,
    get_web_content_service,
)
from app.main import app
from httpx import ASGITransport, AsyncClient


class TestWebContentService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.service = get_web_content_service()

    def test_conservative_markdown_cleaning(self):
        sample_wiki_markdown = """
Jump to content
Main menu
Toggle sidebar
Navigation
* [Main page](https://en.wikipedia.org/wiki/Main_Page)
* [Current events](https://en.wikipedia.org/wiki/Portal:Current_events)
* [Random article](https://en.wikipedia.org/wiki/Special:Random)
* [Donate](https://donate.wikimedia.org)

# Static random-access memory [edit]

Static random-access memory (SRAM) is a type of random-access memory that uses latching circuitry to store each bit.

## Operation

An SRAM cell has three states: standby, reading, and writing. The typical memory cell consists of six MOSFETs (6T cell).

```c
// Example pseudo-code for SRAM read cycle
enable_wordline(addr);
sense_bitlines();
```

### Advantages

* Faster cycle time compared to DRAM
* No periodic refresh required
* Lower power consumption at standby

### Disadvantages

* Higher cost per byte
* Lower density per chip compared to DRAM

Tools
* [What links here](https://en.wikipedia.org/wiki/Special:WhatLinksHere)
* [Permanent link](https://en.wikipedia.org/wiki/Special:PermanentLink)
* [Page information](https://en.wikipedia.org/wiki/Special:PageInformation)

Categories: [Semiconductor memory](https://en.wikipedia.org/wiki/Category:Semiconductor_memory)
This page was last edited on 12 August 2024.
Text is available under the Creative Commons Attribution-ShareAlike License.
"""
        cleaned, confidence = clean_markdown_content(sample_wiki_markdown)

        # 1. Verify boilerplate was removed
        self.assertNotIn("Jump to content", cleaned)
        self.assertNotIn("Main menu", cleaned)
        self.assertNotIn("Toggle sidebar", cleaned)
        self.assertNotIn("Random article", cleaned)
        self.assertNotIn("Donate", cleaned)
        self.assertNotIn("What links here", cleaned)
        self.assertNotIn("This page was last edited on", cleaned)
        self.assertNotIn("Text is available under the Creative Commons", cleaned)

        # 2. Verify legitimate content, headings, and code are preserved
        self.assertIn("# Static random-access memory", cleaned)
        self.assertIn("## Operation", cleaned)
        self.assertIn("### Advantages", cleaned)
        self.assertIn("### Disadvantages", cleaned)
        self.assertIn("latching circuitry to store each bit", cleaned)
        self.assertIn("six MOSFETs (6T cell)", cleaned)
        self.assertIn("enable_wordline(addr);", cleaned)
        self.assertIn("sense_bitlines();", cleaned)

        # 3. High confidence for clean article extraction
        self.assertGreaterEqual(confidence, 0.85)

    def test_chunk_and_rank_large_content(self):
        # Generate a large multi-section document (> 15,000 chars)
        sections = []
        for i in range(1, 25):
            topic_name = f"Topic Section {i}"
            body = f"Detailed explanation for section {i}. This covers algorithmic mechanics, complexity, and systems. " * 30
            if i == 7:
                body += " SPECIAL_KEYWORD_SRAM: Static random-access memory operates using six transistors without needing dynamic capacitor refreshing. " * 5
            sections.append(f"## {topic_name}\n\n{body}")

        large_doc = "\n\n".join(sections)
        self.assertGreater(len(large_doc), 15000)

        # Query specifically for Section 7
        ranked_context = self.service.chunk_and_rank_content(large_doc, "What is SPECIAL_KEYWORD_SRAM?")
        self.assertLessEqual(len(ranked_context), 11000)
        self.assertIn("SPECIAL_KEYWORD_SRAM", ranked_context)
        self.assertIn("Topic Section 7", ranked_context)

    async def test_api_web_fetch_and_ask_routes(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": "Bearer dev_tester"}

            # Test 1: Fetch endpoint with Wikipedia SRAM
            fetch_res = await client.post(
                "/api/web/fetch",
                json={"url": "https://en.wikipedia.org/wiki/Static_random-access_memory"},
                headers=headers,
            )
            self.assertEqual(fetch_res.status_code, 200)
            data = fetch_res.json()
            self.assertTrue(data.get("success"))
            self.assertIn("SRAM", data.get("title", "") + data.get("content", ""))
            self.assertGreater(data.get("word_count", 0), 100)
            self.assertNotIn("Jump to content", data.get("content", ""))
            self.assertNotIn("Main menu", data.get("content", ""))

            # Test 2: Invalid URL error handling
            bad_res = await client.post(
                "/api/web/fetch",
                json={"url": "ftp://bad-scheme.com"},
                headers=headers,
            )
            self.assertEqual(bad_res.status_code, 400)

            # Test 3: Grounded Q&A endpoint
            ask_res = await client.post(
                "/api/web/ask",
                json={
                    "url": "https://en.wikipedia.org/wiki/Static_random-access_memory",
                    "question": "What is SRAM and what are its advantages?",
                },
                headers=headers,
            )
            self.assertEqual(ask_res.status_code, 200)
            ask_data = ask_res.json()
            self.assertTrue(ask_data.get("success"))
            self.assertIn("answer", ask_data)
            self.assertGreater(len(ask_data["answer"]), 50)
            self.assertEqual(ask_data["source"]["url"], "https://en.wikipedia.org/wiki/Static_random-access_memory")

            # Test 4: Grounded Q&A with completely unmentioned query
            unrelated_res = await client.post(
                "/api/web/ask",
                json={
                    "url": "https://en.wikipedia.org/wiki/Static_random-access_memory",
                    "question": "Who scored the winning goal in the 1994 FIFA World Cup Final?",
                },
                headers=headers,
            )
            self.assertEqual(unrelated_res.status_code, 200)
            unrelated_data = unrelated_res.json()
            answer_lower = unrelated_data.get("answer", "").lower()
            self.assertTrue(
                "does not contain" in answer_lower
                or "not enough information" in answer_lower
                or "cannot be found" in answer_lower
                or "does not provide" in answer_lower,
                f"Expected grounded rejection, got: {answer_lower}",
            )

            # Test 5: Verify answer is NOT identical to raw fetched Markdown
            self.assertNotEqual(ask_data["answer"].strip(), data["content"].strip())
            self.assertIn("sram", ask_data["answer"].lower())

            # Test 6: SSRF protection (localhost and private IPs rejected)
            ssrf_res1 = await client.post(
                "/api/web/ask",
                json={"url": "http://localhost:8000/secret", "question": "test"},
                headers=headers,
            )
            self.assertEqual(ssrf_res1.status_code, 400)

            ssrf_res2 = await client.post(
                "/api/web/ask",
                json={"url": "http://127.0.0.1:8080/admin", "question": "test"},
                headers=headers,
            )
            self.assertEqual(ssrf_res2.status_code, 400)

            # Test 7: Synthesize Study Notes from Web URL
            notes_res = await client.post(
                "/api/web/notes",
                json={
                    "url": "https://en.wikipedia.org/wiki/Static_random-access_memory",
                    "topic": "SRAM architecture",
                    "difficulty": "intermediate",
                },
                headers=headers,
            )
            self.assertEqual(notes_res.status_code, 200)
            notes_data = notes_res.json()
            self.assertTrue(notes_data.get("success"))
            self.assertIn("notes", notes_data)
            notes_obj = notes_data["notes"]
            self.assertTrue("sections" in notes_obj or "topic_title" in notes_obj or "title" in notes_obj)

            # Test 8: /api/study/notes with url parameter
            study_notes_res = await client.post(
                "/api/study/notes",
                json={
                    "url": "https://en.wikipedia.org/wiki/Static_random-access_memory",
                    "topic": "SRAM architecture",
                    "difficulty": "intermediate",
                },
                headers=headers,
            )
            self.assertEqual(study_notes_res.status_code, 200)
            study_notes_data = study_notes_res.json()
            self.assertTrue("sections" in study_notes_data or "title" in study_notes_data)


if __name__ == "__main__":
    unittest.main()
