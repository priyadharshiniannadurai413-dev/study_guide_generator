"""
app/ai/mcp_service.py
---------------------
Core Fetch MCP (Model Context Protocol) client service.
Connects to external documentation and academic resources, converts web documents
into clean structured Markdown, and maintains an in-memory TTL cache to optimize latency.

Ensures timeouts, network errors, and anti-bot responses (HTTP 403) fail safely
without interrupting the main application or agent loops.
"""

import asyncio
from datetime import datetime, timezone
import logging
import re
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger("uvicorn")

CACHE_TTL_SECONDS = 900  # 15 minutes
MAX_CACHE_ENTRIES = 150
REQUEST_TIMEOUT_SECONDS = 9.0


class FetchCache:
    """In-memory LRU/TTL cache for fetched web documentation."""

    def __init__(self, ttl: float = CACHE_TTL_SECONDS, max_entries: int = MAX_CACHE_ENTRIES):
        self.ttl = ttl
        self.max_entries = max_entries
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        if url in self._cache:
            data, timestamp = self._cache[url]
            if now - timestamp <= self.ttl:
                # Refresh LRU access
                self._cache[url] = (data, now)
                return data
            else:
                del self._cache[url]
        return None

    def set(self, url: str, data: Dict[str, Any]) -> None:
        now = time.time()
        # Clean expired
        expired = [k for k, (_, ts) in self._cache.items() if now - ts > self.ttl]
        for k in expired:
            self._cache.pop(k, None)
        # Cap size
        if len(self._cache) >= self.max_entries:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            self._cache.pop(oldest, None)
        self._cache[url] = (data, now)


_fetch_cache = FetchCache()


class FetchMCPService:
    """
    Centralized service for Fetch MCP operations.
    Acts as the single point of interaction between LangGraph agents and the web.
    """

    def __init__(self):
        self.cache = _fetch_cache
        self.headers = {
            "User-Agent": "StudySync-Academic-MCP/1.0 (https://studysync.ai; contact@studysync.edu) Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to structured Markdown using html2text with regex fallback."""
        try:
            import html2text

            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_tables = False
            h.body_width = 0
            h.unicode_snob = True
            md = h.handle(html_content)
            return re.sub(r"\n{3,}", "\n\n", md).strip()
        except Exception as exc:
            logger.debug(f"[FetchMCPService] html2text fallback: {exc}")
            text = re.sub(r"<script.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text

    def _extract_title(self, raw_html: str) -> str:
        """Extract document title tag."""
        match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
            return title[:120]
        return "Web Documentation"

    async def fetch_web_content(
        self,
        url: str,
        max_length: int = 20000,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch a specific web page URL and convert to Markdown.
        Returns a standardized payload with title, content, timestamp, and status.
        Never raises exceptions; all network issues return a structured error dictionary.
        """
        url_clean = url.strip()
        if not url_clean:
            return {
                "status": "error",
                "url": url,
                "title": "",
                "content": "",
                "length": 0,
                "error": "Empty URL provided",
            }

        parsed = urlparse(url_clean)
        if not parsed.scheme or parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            return {
                "status": "error",
                "url": url_clean,
                "title": "",
                "content": "",
                "length": 0,
                "error": "Invalid URL format (must be http:// or https:// with valid domain)",
            }

        # Check Cache
        if not bypass_cache:
            cached = self.cache.get(url_clean)
            if cached:
                logger.debug(f"[FetchMCPService] Cache HIT for {url_clean}")
                return cached

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=4.0),
                follow_redirects=True,
                verify=True,
            ) as client:
                response = await client.get(url_clean, headers=self.headers)

                # If anti-bot challenge (403, 401, 503), attempt reader fallback
                if response.status_code in (403, 401, 503):
                    logger.info(f"[FetchMCPService] Status {response.status_code} for {url_clean}. Trying reader fallback...")
                    try:
                        fb_resp = await client.get(f"https://r.jina.ai/{url_clean}", timeout=8.0)
                        if fb_resp.status_code == 200 and fb_resp.text:
                            raw = fb_resp.text
                            title_m = re.search(r"^Title:\s*(.+)$", raw, re.MULTILINE)
                            title = title_m.group(1).strip() if title_m else self._extract_title(raw)
                            parts = re.split(r"Markdown Content:\s*", raw, maxsplit=1)
                            md = parts[1].strip() if len(parts) > 1 else raw.strip()
                            if len(md) > max_length:
                                md = md[:max_length] + f"\n\n... [Content truncated at {max_length} characters]"

                            result = {
                                "status": "success",
                                "url": url_clean,
                                "title": title or "Web Documentation",
                                "content": md,
                                "length": len(md),
                                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                "cached": False,
                                "error": None,
                            }
                            self.cache.set(url_clean, result)
                            return result
                    except Exception as fb_err:
                        logger.warning(f"[FetchMCPService] Reader fallback failed: {fb_err}")

                if response.status_code >= 400:
                    return {
                        "status": "error",
                        "url": url_clean,
                        "title": "",
                        "content": "",
                        "length": 0,
                        "error": f"Remote server returned HTTP {response.status_code} ({response.reason_phrase})",
                    }

                raw_html = response.text
                title = self._extract_title(raw_html)
                markdown = self._html_to_markdown(raw_html)

                if len(markdown) > max_length:
                    markdown = markdown[:max_length] + f"\n\n... [Content truncated at {max_length} characters]"

                result = {
                    "status": "success",
                    "url": str(response.url),
                    "title": title,
                    "content": markdown,
                    "raw_html": raw_html,
                    "length": len(markdown),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "cached": False,
                    "error": None,
                }
                self.cache.set(url_clean, result)
                return result

        except httpx.TimeoutException:
            logger.warning(f"[FetchMCPService] Timeout fetching '{url_clean}'")
            return {
                "status": "error",
                "url": url_clean,
                "title": "",
                "content": "",
                "length": 0,
                "error": "Connection timed out (remote host took too long to respond)",
            }
        except httpx.RequestError as exc:
            logger.warning(f"[FetchMCPService] Network error for '{url_clean}': {exc}")
            return {
                "status": "error",
                "url": url_clean,
                "title": "",
                "content": "",
                "length": 0,
                "error": f"Network request error: {str(exc)}",
            }
        except Exception as exc:
            logger.error(f"[FetchMCPService] Unexpected error for '{url_clean}': {exc}")
            return {
                "status": "error",
                "url": url_clean,
                "title": "",
                "content": "",
                "length": 0,
                "error": f"Internal fetch error: {str(exc)}",
            }

    async def search_and_fetch_topic(self, topic: str, max_length: int = 15000) -> Dict[str, Any]:
        """
        When the agent needs external documentation on a topic but does not have a direct URL,
        derive an authoritative academic reference (e.g. Wikipedia / Python docs / RFC) and fetch it.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            return {"status": "error", "error": "Empty topic"}

        # Format topic into a canonical reference URL
        slug = re.sub(r"[^\w\s-]", "", clean_topic).strip()
        slug = re.sub(r"[\s_]+", "_", slug)
        candidate_url = f"https://en.wikipedia.org/wiki/{quote_plus(slug)}"

        logger.info(f"[FetchMCPService] Resolving topic '{clean_topic}' via canonical reference: {candidate_url}")
        res = await self.fetch_web_content(candidate_url, max_length=max_length)
        if res.get("status") == "success":
            return res

        # If direct Wikipedia title not found, return empty result gracefully
        return {
            "status": "error",
            "url": candidate_url,
            "title": "",
            "content": "",
            "length": 0,
            "error": f"No authoritative public documentation found for topic: {clean_topic}",
        }


# Singleton instance
_fetch_service: Optional[FetchMCPService] = None


def get_fetch_mcp_service() -> FetchMCPService:
    """Return the singleton instance of FetchMCPService."""
    global _fetch_service
    if _fetch_service is None:
        _fetch_service = FetchMCPService()
    return _fetch_service


__all__ = ["FetchMCPService", "get_fetch_mcp_service"]
