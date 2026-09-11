"""
scripts/test_mcp_connectors.py
------------------------------
Unit and integration test suite for MCP Connectors backend routes:
- /api/integrations/status
- /api/integrations/health
- /api/tools/fetch-url (validation, conversion, error handling)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.tools import _html_to_clean_markdown, _extract_page_title


class TestMCPConnectorsBackend(unittest.TestCase):

    def test_html_to_markdown_conversion(self):
        """Test that HTML is cleanly transformed to Markdown."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>SRAM Architecture Overview</title></head>
        <body>
            <h1>Static Random-Access Memory (SRAM)</h1>
            <p>SRAM uses <strong>bistable latching circuitry</strong> to store each bit.</p>
            <ul>
                <li>Volatile memory</li>
                <li>Fast access time</li>
                <li>Six-transistor (6T) memory cell</li>
            </ul>
        </body>
        </html>
        """
        title = _extract_page_title(sample_html)
        self.assertEqual(title, "SRAM Architecture Overview")

        markdown = _html_to_clean_markdown(sample_html)
        self.assertIn("# Static Random-Access Memory (SRAM)", markdown)
        self.assertIn("bistable latching circuitry", markdown)
        self.assertIn("Six-transistor (6T) memory cell", markdown)

    def test_url_validation_error_handling(self):
        """Verify that invalid and malformed URLs raise HTTPException instead of crashing."""
        import asyncio
        from fastapi import HTTPException
        from app.routes.tools import _execute_fetch

        # Test empty URL
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(_execute_fetch("", 5000))
        self.assertEqual(ctx.exception.status_code, 400)

        # Test non-http/https protocol
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(_execute_fetch("ftp://example.com/file", 5000))
        self.assertEqual(ctx.exception.status_code, 400)

        # Test missing domain
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(_execute_fetch("http://", 5000))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_router_endpoints_registered(self):
        """Verify that integrations and tools routes are properly registered on the FastAPI app."""
        from app.main import app

        route_paths = list(app.openapi()["paths"].keys())
        self.assertIn("/api/integrations/status", route_paths)
        self.assertIn("/api/integrations/health", route_paths)
        self.assertIn("/api/integrations/github", route_paths)
        self.assertIn("/api/tools/fetch-url", route_paths)


if __name__ == "__main__":
    unittest.main()
