"""
app/routes/tools.py
-------------------
FastAPI router for external tool proxies and testing utilities, including the
Fetch MCP (Model Context Protocol) web reader proxy.

Endpoints:
    GET  /api/tools/fetch-url?url=...  → Fetch external web doc and convert to Markdown
    POST /api/tools/fetch-url          → Fetch external web doc via JSON body
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/tools", tags=["tools"])


class FetchURLRequest(BaseModel):
    url: str = Field(..., description="Absolute web documentation or textbook URL (http/https)")
    max_length: Optional[int] = Field(default=20000, ge=500, le=100000, description="Max character length")


def _html_to_clean_markdown(html_content: str) -> str:
    """Convert raw HTML into structured, readable Markdown."""
    try:
        import html2text

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_tables = False
        h.body_width = 0  # Do not wrap lines
        h.unicode_snob = True
        md = h.handle(html_content)
        # Collapse multiple blank lines
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        return md
    except Exception as exc:
        logger.warning(f"[tools.py] html2text conversion warning: {exc}; using fallback tag stripping")
        # Fallback basic tag stripper
        text = re.sub(r"<script.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def _extract_page_title(html_content: str) -> str:
    """Extract HTML document title if present."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html_content, flags=re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        title = re.sub(r"\s+", " ", title)
        return title[:120]
    return "Web Documentation"


async def _execute_fetch(target_url: str, max_length: int) -> dict:
    """Validate, fetch, and convert web documentation to clean Markdown."""
    url_clean = target_url.strip()
    if not url_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL parameter cannot be empty.",
        )

    # Validate URL structure and scheme
    parsed = urlparse(url_clean)
    if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL protocol '{parsed.scheme}'. Only 'http://' and 'https://' URLs are supported.",
        )
    if not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed URL: Missing valid domain or host name.",
        )

    headers = {
        "User-Agent": "StudySync-Academic-MCP/1.0 (https://studysync.ai; contact@studysync.edu) Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=6.0),
            follow_redirects=True,
            verify=True,
        ) as client:
            response = await client.get(url_clean, headers=headers)

            if response.status_code in (403, 401, 503):
                logger.info(f"[tools.py] Direct fetch returned {response.status_code}. Attempting reader fallback via r.jina.ai...")
                try:
                    fallback_resp = await client.get(f"https://r.jina.ai/{url_clean}", timeout=10.0)
                    if fallback_resp.status_code == 200 and fallback_resp.text:
                        raw_text = fallback_resp.text
                        title_match = re.search(r"^Title:\s*(.+)$", raw_text, re.MULTILINE)
                        title = title_match.group(1).strip() if title_match else _extract_page_title(raw_text)
                        content_parts = re.split(r"Markdown Content:\s*", raw_text, maxsplit=1)
                        markdown = content_parts[1].strip() if len(content_parts) > 1 else raw_text.strip()
                        if len(markdown) > max_length:
                            markdown = markdown[:max_length] + f"\n\n... [Content truncated at {max_length} characters]"
                        return {
                            "status": "success",
                            "url": url_clean,
                            "title": title or "Web Documentation",
                            "markdown_content": markdown,
                            "length": len(markdown),
                        }
                except Exception as fb_err:
                    logger.warning(f"[tools.py] Reader fallback also encountered error: {fb_err}")

            if response.status_code >= 400:
                logger.warning(f"[tools.py] Remote URL '{url_clean}' returned HTTP {response.status_code}")
                if response.status_code == 403:
                    detail_msg = (
                        "Target web server denied access (HTTP 403 Forbidden). "
                        "The website enforces anti-bot or login protections. "
                        "Please try another public documentation URL (e.g. Python docs, MDN, or Wikipedia)."
                    )
                else:
                    detail_msg = f"Target web server responded with HTTP error {response.status_code} ({response.reason_phrase})."
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=detail_msg,
                )

            raw_html = response.text
            title = _extract_page_title(raw_html)
            markdown = _html_to_clean_markdown(raw_html)

            if len(markdown) > max_length:
                markdown = markdown[:max_length] + f"\n\n... [Content truncated at {max_length} characters]"

            return {
                "status": "success",
                "url": str(response.url),
                "title": title,
                "markdown_content": markdown,
                "length": len(markdown),
            }

    except httpx.TimeoutException:
        logger.warning(f"[tools.py] Timeout fetching '{url_clean}'")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Connection to target URL timed out. The remote host took too long to respond.",
        )
    except httpx.ConnectError as exc:
        logger.warning(f"[tools.py] Connect error for '{url_clean}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to host: {exc}. Please verify the domain is reachable.",
        )
    except httpx.RequestError as exc:
        logger.warning(f"[tools.py] Request error for '{url_clean}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network request error: {exc}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[tools.py] Unexpected error fetching '{url_clean}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during web extraction: {exc}",
        )


@router.get("/fetch-url")
async def fetch_url_get(
    url: str = Query(..., description="Web documentation URL to fetch"),
    max_length: int = Query(20000, ge=500, le=100000),
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch external documentation URL and convert to clean Markdown.
    Supports GET queries from the FetchConnectorCard live test UI.
    """
    return await _execute_fetch(url, max_length)


@router.post("/fetch-url")
async def fetch_url_post(
    payload: FetchURLRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch external documentation URL and convert to clean Markdown via JSON body.
    """
    return await _execute_fetch(payload.url, payload.max_length or 20000)


__all__ = ["router"]
