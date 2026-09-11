"""
app/ai/source_validator.py
--------------------------
Source validation and multi-tier quality evaluation for external web pages
fetched via Fetch MCP. Ensures only high-yield, academically credible references
are injected into the LangGraph evidence stream.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("uvicorn")

# Tier 1: Authoritative academic domains, specifications, and primary vendor documentation
TIER_1_DOMAINS = {
    "docs.python.org",
    "developer.mozilla.org",
    "fastapi.tiangolo.com",
    "react.dev",
    "nodejs.org",
    "ietf.org",
    "w3.org",
    "kernel.org",
    "oracle.com",
    "spring.io",
    "kubernetes.io",
    "docker.com",
    "mongodb.com",
    "postgresql.org",
    "redis.io",
    "golang.org",
    "rust-lang.org",
    "apache.org",
    "ieee.org",
    "acm.org",
}

# Tier 2: General reference, open encyclopedias, open preprints, and developer portals
TIER_2_DOMAINS = {
    "wikipedia.org",
    "arxiv.org",
    "github.com",
    "geeksforgeeks.org",
    "tutorialspoint.com",
    "stackoverflow.com",
    "w3schools.com",
}

# Strictly rejected domains (social media, video hubs, commercial ad spam)
BLOCKED_DOMAINS = {
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "reddit.com",
    "pinterest.com",
    "youtube.com",
    "quora.com",
}


def evaluate_domain_tier(domain: str) -> str:
    """Classify domain into tier_1, tier_2, or general."""
    clean_domain = domain.lower()
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]

    # Academic & governmental TLDs
    if clean_domain.endswith(".edu") or clean_domain.endswith(".gov") or clean_domain.endswith(".ac.uk"):
        return "tier_1_academic"

    # Explicit Tier 1 domains or subdomains
    for t1 in TIER_1_DOMAINS:
        if clean_domain == t1 or clean_domain.endswith("." + t1):
            return "tier_1_spec"

    # Explicit Tier 2 domains
    for t2 in TIER_2_DOMAINS:
        if clean_domain == t2 or clean_domain.endswith("." + t2):
            return "tier_2_reference"

    # Blocked domains
    for bl in BLOCKED_DOMAINS:
        if clean_domain == bl or clean_domain.endswith("." + bl):
            return "blocked"

    return "general_web"


def validate_web_source(raw_fetch_result: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Validate and score a fetched web page for academic suitability.

    Returns:
        (is_valid, validated_source_dict, rejection_reason)
    """
    if not raw_fetch_result or raw_fetch_result.get("status") != "success":
        err = raw_fetch_result.get("error") if raw_fetch_result else "No result returned"
        return False, {}, f"Fetch failed: {err}"

    url = raw_fetch_result.get("url", "").strip()
    content = raw_fetch_result.get("content", "").strip()
    title = raw_fetch_result.get("title", "Web Documentation").strip()

    if not url:
        return False, {}, "Missing URL"

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    tier = evaluate_domain_tier(domain)

    if tier == "blocked":
        return False, {}, f"Domain '{domain}' is in the restricted academic domain list"

    # Content length heuristics: must have substantial textual material
    if len(content) < 120:
        return False, {}, f"Content is too brief ({len(content)} characters) to provide factual evidence"

    # Reject typical error pages that returned 200 OK
    lower_content = content.lower()
    error_markers = [
        "page not found",
        "404 not found",
        "access denied",
        "enable javascript to continue",
        "checking your browser before accessing",
        "security verification",
        "please verify you are a human",
    ]
    for marker in error_markers:
        if marker in lower_content[:400]:
            return False, {}, f"Page contains error or verification barrier marker: '{marker}'"

    validated_item = {
        "source_type": "web",
        "url": url,
        "domain": domain,
        "title": title,
        "tier": tier,
        "retrieved_at": raw_fetch_result.get("retrieved_at") or datetime.now(timezone.utc).isoformat(),
        "length": len(content),
        "content": content,
        "valid": True,
    }

    return True, validated_item, None


def format_combined_evidence(
    rag_chunks: List[Dict[str, Any]],
    web_sources: List[Dict[str, Any]],
    max_rag_chars: int = 12000,
    max_web_chars: int = 8000,
) -> str:
    """
    Combine MongoDB Vector RAG evidence and Fetch MCP web evidence
    using strict, unmistakable source boundaries.
    """
    sections = []

    # 1. RAG Section
    if rag_chunks:
        rag_parts = ["=== UPLOADED DOCUMENT EVIDENCE ==="]
        running_len = 0
        for i, chunk in enumerate(rag_chunks, start=1):
            source_name = chunk.get("doc_id") or chunk.get("source") or "Course Syllabus"
            page = chunk.get("page_number", "?")
            text = chunk.get("text", "").strip()
            if not text:
                continue

            entry = f"[Doc Chunk {i} | Source: {source_name} | Page {page}]\n{text}"
            if running_len + len(entry) > max_rag_chars:
                rag_parts.append(f"[Remaining {len(rag_chunks) - i} document chunks truncated for context budget]")
                break
            rag_parts.append(entry)
            running_len += len(entry)

        sections.append("\n\n".join(rag_parts))
    else:
        sections.append("=== UPLOADED DOCUMENT EVIDENCE ===\n(No direct matches found in uploaded course documents)")

    # 2. Web Section
    if web_sources:
        web_parts = ["=== EXTERNAL WEB EVIDENCE (FETCH MCP) ==="]
        running_len = 0
        for j, w_src in enumerate(web_sources, start=1):
            title = w_src.get("title", "Online Documentation")
            url = w_src.get("url", "")
            tier = w_src.get("tier", "web")
            content = w_src.get("content", "").strip()

            entry = f"[Web Source {j} | {title} | Quality: {tier}]\nURL: {url}\n\n{content}"
            if running_len + len(entry) > max_web_chars:
                web_parts.append(f"[Remaining web source text truncated for context budget]")
                break
            web_parts.append(entry)
            running_len += len(entry)

        sections.append("\n\n".join(web_parts))

    return "\n\n\n".join(sections)


__all__ = [
    "evaluate_domain_tier",
    "validate_web_source",
    "format_combined_evidence",
    "TIER_1_DOMAINS",
    "TIER_2_DOMAINS",
]
