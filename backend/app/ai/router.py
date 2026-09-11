"""
app/ai/router.py
----------------
Hybrid Intent Router for AI Study Assistant.

Combines Layer 1 (fast zero-latency regex matching) with Layer 2
(lightweight LLM classification via Google Gemini 1.5 Flash fallback).
Note: The legacy CGPA calculator intent has been completely excluded.
"""

import logging
import re
from enum import Enum
from typing import Optional

logger = logging.getLogger("uvicorn")


class Intent(str, Enum):
    GREETING = "GREETING"
    SYLLABUS = "SYLLABUS"
    STUDY_MATERIAL = "STUDY_MATERIAL"
    GITHUB = "GITHUB"
    WEB_SEARCH = "WEB_SEARCH"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# Layer 1: Regex Pattern Matchers
# ==============================================================================

# Common standalone conversational greetings
GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening|day)|howdy|sup|who\s+are\s+you|what\s+can\s+you\s+do)\b",
    re.IGNORECASE,
)

# Syllabus & Curriculum inquiries
SYLLABUS_RE = re.compile(
    r"\b(unit|semester|sem|regulation|syllabus|curriculum|course\s*code|subject\s*code|credits?|module|objectives?|outcomes?|topics?|theory|practical|lab\s*manual|department)\b",
    re.IGNORECASE,
)

# Study generation inquiries (MCQs, notes, summaries, quizzes)
STUDY_MATERIAL_RE = re.compile(
    r"\b(summarize|summary|mcqs?|flashcards?|quiz|quizzes|study\s*(guide|notes)|practice\s*questions?|revision\s*notes?|key\s*concepts?|formulas?|exam\s*prep|generate\s*questions?)\b",
    re.IGNORECASE,
)

# GitHub repository, branch, PR, commit operations
GITHUB_RE = re.compile(
    r"\b(repos?|repository|repositories|commits?|prs?|pull\s*requests?|branch(es)?|issues?|forks?|merge|diff|clone|github|git\s*(status|log|push|pull))\b",
    re.IGNORECASE,
)

# Live web search queries (placements, news, trends, careers)
WEB_SEARCH_RE = re.compile(
    r"\b(latest|current|news|trends?|placements?|salary|salaries|packages?|recruit(ment)?|companies|hiring|gate\s*exam|interview\s*questions?)\b",
    re.IGNORECASE,
)


def _classify_regex(query: str) -> Optional[Intent]:
    """Fast Layer 1 regex classifier returning an Intent or None if ambiguous."""
    clean_query = query.strip()
    if not clean_query:
        return Intent.GREETING

    # 1. Direct short greeting check
    if GREETING_RE.search(clean_query) and len(clean_query.split()) <= 5:
        return Intent.GREETING

    # 2. GitHub takes precedence if git/repo operations are detected
    if GITHUB_RE.search(clean_query):
        return Intent.GITHUB

    # 3. Study material generation keywords
    if STUDY_MATERIAL_RE.search(clean_query):
        return Intent.STUDY_MATERIAL

    # 4. Syllabus / curriculum keywords
    if SYLLABUS_RE.search(clean_query):
        return Intent.SYLLABUS

    # 5. Live web search keywords
    if WEB_SEARCH_RE.search(clean_query):
        return Intent.WEB_SEARCH

    # 6. Fallback to greeting if matched in longer text
    if GREETING_RE.search(clean_query):
        return Intent.GREETING

    return None


# ==============================================================================
# Layer 2: LLM Fallback (Google Gemini Flash)
# ==============================================================================

def _classify_llm(query: str) -> Intent:
    """Layer 2 lightweight LLM classifier for queries that pass through regex."""
    prompt = (
        "You are an intent classifier for a university academic assistant. "
        "Classify the following student query into exactly ONE of the following intents:\n"
        "- GREETING: Casual hello or introductory question\n"
        "- SYLLABUS: Questions regarding course units, semester topics, curriculum, subject regulations\n"
        "- STUDY_MATERIAL: Requests to create study notes, summaries, MCQs, quizzes, flashcards\n"
        "- GITHUB: Requests to list repos, commits, PRs, issues, or interact with GitHub\n"
        "- WEB_SEARCH: Questions about latest placement trends, news, hiring packages, or industry news\n"
        "- UNKNOWN: Ambiguous or general domain questions\n\n"
        f"Query: \"{query.strip()}\"\n"
        "Output ONLY the intent name without any preamble, markdown, or punctuation."
    )

    try:
        from app.ai.models import get_router_llm

        llm = get_router_llm()
        response = llm.invoke(prompt)
        raw_text = response.content
        if isinstance(raw_text, list):
            raw_text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw_text)
        pred = str(raw_text).strip().upper()

        for intent in Intent:
            if intent.value in pred:
                return intent
    except Exception as exc:
        logger.warning(f"[Router] LLM classification error ({exc}); returning UNKNOWN.")

    return Intent.UNKNOWN


# ==============================================================================
# Public Router Interface
# ==============================================================================

def route_query(query: str) -> Intent:
    """
    Classify user query into an actionable intent using hybrid Layer 1 + Layer 2.

    Args:
        query: Raw prompt from user.

    Returns:
        Intent enum member.
    """
    # 1. Fast Layer 1 Regex
    regex_intent = _classify_regex(query)
    if regex_intent is not None:
        return regex_intent

    # 2. Layer 2 LLM Fallback
    return _classify_llm(query)


async def aroute_query(query: str) -> Intent:
    """Async non-blocking wrapper around route_query."""
    regex_intent = _classify_regex(query)
    if regex_intent is not None:
        return regex_intent

    import asyncio
    return await asyncio.to_thread(_classify_llm, query)


__all__ = ["Intent", "route_query", "aroute_query"]
