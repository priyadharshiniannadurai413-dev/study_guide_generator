"""
app/ai/models.py
-----------------
Centralized LLM provider factory using native LangChain integrations.

Fallback chain:
  1. Primary   → Mistral Small  (mistral-small-latest)  via langchain-mistralai
  2. Fallback  → Groq           (gpt-oss-20b)           via langchain-groq
  3. Fallback  → Gemini         (gemini-flash-lite-latest) via langchain-google-genai

All agent nodes import from this module — never instantiate LLMs directly.
"""

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger("uvicorn")

# ── Model identifiers ────────────────────────────────────────────────────────
PRIMARY_MODEL = "mistral-small-latest"
FALLBACK_MODEL = "openai/gpt-oss-20b"
LIGHTWEIGHT_MODEL = "gemini-3.5-flash-lite"
ROUTER_MODEL = "gemini-3.5-flash-lite"

# ── Default inference parameters ──────────────────────────────────────────────
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4096


def get_primary_llm(
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Instantiate Mistral Small as the primary LLM.

    Returns:
        ChatMistralAI instance bound to mistral-small-latest.
    """
    from langchain_mistralai import ChatMistralAI

    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY is not configured. "
            "Add MISTRAL_API_KEY to your .env file."
        )

    return ChatMistralAI(
        model=PRIMARY_MODEL,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def get_fallback_llm(
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Instantiate Groq gpt-oss-20b as the first fallback LLM.

    Returns:
        ChatGroq instance bound to gpt-oss-20b.
    """
    from langchain_groq import ChatGroq

    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not configured. "
            "Add GROQ_API_KEY to your .env file."
        )

    return ChatGroq(
        model=FALLBACK_MODEL,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def get_lightweight_llm(
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Instantiate Gemini flash-lite as the lightweight / last-resort fallback.

    Returns:
        ChatGoogleGenerativeAI instance bound to gemini-flash-lite-latest.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. "
            "Add GEMINI_API_KEY to your .env file."
        )

    return ChatGoogleGenerativeAI(
        model=LIGHTWEIGHT_MODEL,
        google_api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def get_llm_with_fallback(
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Return the primary LLM wrapped with automatic fallbacks.

    Chain: Mistral Small → Groq gpt-oss-20b → Gemini flash-lite.
    Uses LangChain's native `with_fallbacks()` mechanism so callers
    never need to handle provider errors manually.

    Returns:
        BaseChatModel with fallback chain attached.
    """
    primary = get_primary_llm(temperature=temperature, max_tokens=max_tokens, **kwargs)

    fallbacks: list[BaseChatModel] = []

    # Groq fallback
    try:
        groq_llm = get_fallback_llm(temperature=temperature, max_tokens=max_tokens, **kwargs)
        fallbacks.append(groq_llm)
    except ValueError:
        logger.warning("[Models] GROQ_API_KEY not set — Groq fallback unavailable.")

    # Gemini fallback
    try:
        gemini_llm = get_lightweight_llm(temperature=temperature, max_tokens=max_tokens, **kwargs)
        fallbacks.append(gemini_llm)
    except ValueError:
        logger.warning("[Models] GEMINI_API_KEY not set — Gemini fallback unavailable.")

    if fallbacks:
        return primary.with_fallbacks(fallbacks)

    return primary


def get_router_llm(
    temperature: float = 0.0,
    max_tokens: int = 50,
) -> BaseChatModel:
    """
    Return a cheap, fast LLM used exclusively for intent classification
    in the supervisor router node.

    Uses Gemini flash-lite (gemini-3.5-flash-lite) for minimal latency and cost.
    Automatically falls back to Groq (openai/gpt-oss-20b) if Gemini errors out.
    """
    gemini_llm = None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.GEMINI_API_KEY
        if api_key:
            gemini_llm = ChatGoogleGenerativeAI(
                model=ROUTER_MODEL,
                google_api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
    except Exception as exc:
        logger.warning(f"[Models] Gemini router init failed ({exc}); trying Groq.")

    groq_llm = None
    try:
        groq_llm = get_fallback_llm(temperature=temperature, max_tokens=max_tokens)
    except Exception as exc:
        logger.warning(f"[Models] Groq router fallback init failed ({exc}).")

    if gemini_llm and groq_llm:
        return gemini_llm.with_fallbacks([groq_llm])
    elif gemini_llm:
        return gemini_llm
    elif groq_llm:
        return groq_llm

    return get_primary_llm(temperature=temperature, max_tokens=max_tokens)


__all__ = [
    "PRIMARY_MODEL",
    "FALLBACK_MODEL",
    "LIGHTWEIGHT_MODEL",
    "get_primary_llm",
    "get_fallback_llm",
    "get_lightweight_llm",
    "get_llm_with_fallback",
    "get_router_llm",
]
