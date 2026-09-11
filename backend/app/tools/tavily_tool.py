"""
app/tools/tavily_tool.py
------------------------
Web search tool using Tavily Search API.
Lazy-initialized so a missing TAVILY_API_KEY does not crash the server at startup,
returning a helpful explanatory message if invoked without credentials.
"""

import logging
from typing import Any, List, Optional
from langchain_core.tools import tool
from app.core.config import settings

logger = logging.getLogger("uvicorn")

_tavily_client: Optional[Any] = None


def _get_tavily_client() -> Optional[Any]:
    """Return a cached TavilySearchResults client, or None if key is missing/uninstalled."""
    global _tavily_client
    if _tavily_client is not None:
        return _tavily_client

    api_key = getattr(settings, "TAVILY_API_KEY", None)
    if not api_key:
        logger.warning("[TavilyTool] TAVILY_API_KEY is not set in environment.")
        return None

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        _tavily_client = TavilySearchResults(
            max_results=3,
            tavily_api_key=api_key,
        )
        return _tavily_client
    except Exception as exc:
        logger.warning(f"[TavilyTool] Failed to initialize TavilySearchResults: {exc}")
        # Try direct langchain_tavily fallback if available
        try:
            from langchain_tavily import TavilySearch

            _tavily_client = TavilySearch(
                max_results=3,
                tavily_api_key=api_key,
            )
            return _tavily_client
        except Exception as exc2:
            logger.error(f"[TavilyTool] Tavily initialization failed: {exc2}")
            return None


@tool
def web_search_tool(query: str) -> str:
    """
    Search the live web for current information not found in the local syllabus database.

    Use this tool ONLY for:
    - Current industry recruitment trends, placement statistics, or gate exam patterns
    - General engineering career questions, technology roadmaps, and certifications
    - External updates or topics explicitly outside GCE Bargur's 2022 regulation syllabus

    Do NOT use this tool for specific college course subjects, credit structures,
    or syllabus units — use syllabus_rag_search instead.

    Args:
        query: Specific search query string to look up online.

    Returns:
        Formatted summary of the top 3 web search results with titles and links.
    """
    client = _get_tavily_client()
    if client is None:
        return (
            "Web search is currently unavailable. Please configure the TAVILY_API_KEY "
            "environment variable to enable live internet searches."
        )

    try:
        results = client.invoke({"query": query})
        if not results:
            return "No web results found for the specified query."

        if isinstance(results, list):
            snippets: List[str] = []
            for item in results[:3]:
                if isinstance(item, dict):
                    title = item.get("title", "Web Result")
                    url = item.get("url", "")
                    content = item.get("content", "").strip()
                    snippets.append(f"**{title}**\nSource: {url}\n{content}")
                else:
                    snippets.append(str(item))
            return "\n\n".join(snippets)

        return str(results)
    except Exception as exc:
        logger.error(f"[web_search_tool] Search failed: {exc}")
        return f"Web search encountered an error: {exc}"
