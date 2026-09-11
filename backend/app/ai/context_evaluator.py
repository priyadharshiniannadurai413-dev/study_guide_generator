"""
app/ai/context_evaluator.py
---------------------------
Sufficiency evaluation and web routing node for LangGraph agents.
Determines whether MongoDB Vector RAG evidence is sufficient to answer the prompt
or if external documentation must be dynamically fetched via Fetch MCP.
"""

import logging
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from app.ai.mcp_service import get_fetch_mcp_service
from app.ai.source_validator import format_combined_evidence, validate_web_source
from app.ai.state import SupervisorState

logger = logging.getLogger("uvicorn")

# Explicit patterns indicating the student wants external web or documentation references
WEB_INTENT_PATTERNS = [
    r"\b(search\s+the\s+web|look\s+up\s+online|search\s+online)\b",
    r"\b(official\s+docs?|official\s+documentation|online\s+docs?)\b",
    r"\b(check\s+the\s+docs?|external\s+sources?|web\s+references?)\b",
    r"\b(latest\s+version|specifications?|rfc\s*\d+)\b",
    r"\bhttps?://[^\s]+\b",
]


def extract_url_from_text(text: str) -> Optional[str]:
    """Extract first valid HTTP/HTTPS URL from text if present."""
    match = re.search(r"https?://[^\s<>\"']+", text)
    if match:
        url = match.group(0).rstrip(".,;!?:")
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return url
    return None


def evaluate_context_sufficiency(state: SupervisorState) -> Tuple[bool, float, Optional[str], str]:
    """
    Evaluate whether retrieved RAG context is sufficient.

    Returns:
        (is_sufficient, score, candidate_url_or_topic, reasoning)
    """
    user_query = state.get("user_query", "")
    rag_context = state.get("retrieved_context", "") or state.get("rag_context", "")
    enable_web = state.get("enable_web", False)

    # 1. Direct URL check: if query contains a URL, always fetch it
    found_url = extract_url_from_text(user_query)
    if found_url:
        return False, 0.0, found_url, "User query contains direct web URL for inspection"

    # 2. Explicit web intent check
    for pat in WEB_INTENT_PATTERNS:
        if re.search(pat, user_query, re.IGNORECASE):
            return False, 0.2, user_query, "User explicitly requested external web documentation"

    # 3. If web enrichment is explicitly turned ON by the user
    if enable_web:
        # If RAG context is minimal or absent, prioritize web
        if not rag_context or len(rag_context.strip()) < 300 or "No relevant academic content found" in rag_context:
            return False, 0.1, user_query, "Web enrichment enabled and RAG context is sparse"
        # If RAG is moderate, we still enrich with web documentation
        return False, 0.5, user_query, "Web enrichment enabled for complete multi-source coverage"

    # 4. Automatic RAG sufficiency assessment
    if not rag_context or "No relevant academic content found" in rag_context or "Retrieval error" in rag_context:
        # Only fallback to web if syllabus / documents were empty
        return False, 0.0, user_query, "Local course materials yielded no relevant chunks"

    if len(rag_context.strip()) >= 500:
        return True, 0.9, None, "Local course documents provide sufficient context"

    return True, 0.7, None, "Local documents provide acceptable coverage"


async def evaluate_context_node(state: SupervisorState) -> Dict[str, Any]:
    """
    LangGraph node: Evaluates RAG evidence and determines if Fetch MCP is needed.
    """
    is_sufficient, score, target, reason = evaluate_context_sufficiency(state)
    logger.info(f"[ContextEvaluator] Sufficiency: {is_sufficient} (score={score:.2f}) — {reason}")

    return {
        "web_sufficiency_score": score,
        "web_target_url": target if not is_sufficient else None,
    }


def route_after_evaluation(state: SupervisorState) -> str:
    """
    Conditional edge router:
    Returns 'fetch_web' if external enrichment is warranted, otherwise 'generate'.
    """
    score = state.get("web_sufficiency_score", 1.0)
    target = state.get("web_target_url")
    enable_web = state.get("enable_web", False)

    if target or (enable_web and score < 0.8) or score < 0.6:
        return "fetch_web"
    return "generate"


async def fetch_web_node(state: SupervisorState) -> Dict[str, Any]:
    """
    LangGraph node: Fetches external documentation using FetchMCPService.
    Guaranteed non-crashing — always catches errors and logs cleanly.
    """
    target = state.get("web_target_url") or state.get("user_query", "")
    fetch_service = get_fetch_mcp_service()

    found_url = extract_url_from_text(target)
    try:
        if found_url:
            raw_res = await fetch_service.fetch_web_content(found_url, max_length=15000)
        else:
            raw_res = await fetch_service.search_and_fetch_topic(target, max_length=12000)

        if raw_res.get("status") == "success":
            return {
                "web_context": raw_res.get("content", ""),
                "web_sources": [raw_res],
                "web_fetch_error": None,
            }
        else:
            logger.warning(f"[FetchWebNode] Fetch unsuccessful: {raw_res.get('error')}")
            return {
                "web_context": "",
                "web_sources": [],
                "web_fetch_error": raw_res.get("error"),
            }
    except Exception as exc:
        logger.error(f"[FetchWebNode] Exception during fetch: {exc}")
        return {
            "web_context": "",
            "web_sources": [],
            "web_fetch_error": str(exc),
        }


async def validate_web_node(state: SupervisorState) -> Dict[str, Any]:
    """
    LangGraph node: Validates fetched web context against academic criteria
    and synthesizes the combined RAG + Web evidence block.
    """
    raw_sources = state.get("web_sources") or []
    rag_context = state.get("retrieved_context") or state.get("rag_context") or ""
    validated_sources = []

    for raw in raw_sources:
        is_valid, item, reason = validate_web_source(raw)
        if is_valid:
            # Apply conservative boilerplate cleaner
            from app.ai.web_content_service import clean_markdown_content
            clean_text, _ = clean_markdown_content(item.get("content", ""))
            item["content"] = clean_text
            item["length"] = len(clean_text)
            validated_sources.append(item)
        else:
            logger.info(f"[ValidateWebNode] Rejected source '{raw.get('url')}': {reason}")

    # Format structured evidence boundaries
    rag_chunks = [{"text": rag_context, "doc_id": state.get("doc_id", "syllabus")}] if rag_context else []
    combined = format_combined_evidence(rag_chunks, validated_sources)

    return {
        "web_sources": validated_sources,
        "combined_context": combined,
        "retrieved_context": combined,  # Ensure downstream generators transparently receive enriched text
    }


__all__ = [
    "evaluate_context_sufficiency",
    "evaluate_context_node",
    "route_after_evaluation",
    "fetch_web_node",
    "validate_web_node",
    "extract_url_from_text",
]
