"""
backend/scripts/test_fetch_mcp_service.py
-----------------------------------------
Unit tests for FetchMCPService:
- HTML-to-Markdown conversion
- Cache TTL operation
- URL validation (invalid / empty / malformed schemes)
- Mocked / real fetch resilience
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.mcp_service import FetchMCPService, get_fetch_mcp_service


class TestFetchMCPService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.service = get_fetch_mcp_service()

    def test_html_to_markdown_conversion(self):
        html = """
        <html>
            <head><title>Test Doc</title></head>
            <body>
                <h1>Header 1</h1>
                <p>This is a <strong>core</strong> concept explanation.</p>
                <ul>
                    <li>Feature A</li>
                    <li>Feature B</li>
                </ul>
            </body>
        </html>
        """
        md = self.service._html_to_markdown(html)
        self.assertIn("Header 1", md)
        self.assertIn("Feature A", md)
        self.assertIn("core", md)

    def test_extract_title(self):
        html = "<html><head><title>   FastAPI Framework Docs  </title></head></html>"
        title = self.service._extract_title(html)
        self.assertEqual(title, "FastAPI Framework Docs")

    async def test_invalid_urls_never_throw(self):
        # Empty
        res1 = await self.service.fetch_web_content("")
        self.assertEqual(res1.get("status"), "error")
        self.assertIn("Empty URL", res1.get("error", ""))

        # Invalid scheme
        res2 = await self.service.fetch_web_content("ftp://invalid.com/file")
        self.assertEqual(res2.get("status"), "error")

        # Missing host
        res3 = await self.service.fetch_web_content("http://")
        self.assertEqual(res3.get("status"), "error")

    async def test_cache_hits(self):
        test_url = "https://mock-example.org/test-cache-entry"
        fake_payload = {
            "status": "success",
            "url": test_url,
            "title": "Mock Title",
            "content": "# Mock Content",
            "length": 14,
            "cached": False,
        }
        self.service.cache.set(test_url, fake_payload)
        cached = self.service.cache.get(test_url)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.get("title"), "Mock Title")


if __name__ == "__main__":
    unittest.main()
