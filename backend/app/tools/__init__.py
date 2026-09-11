"""
app/tools
---------
Central local tool registry for the AI Study Assistant.
Provides access to syllabus RAG search and live internet fallback search.
Note: The CGPA calculator tool has been deliberately excluded.
"""

from typing import Dict, List

from langchain_core.tools import BaseTool

from .rag_tool import syllabus_rag_search, syllabus_rag_search_async
from .tavily_tool import web_search_tool

# Central list of active local tools
LOCAL_TOOLS: List[BaseTool] = [syllabus_rag_search, web_search_tool]

# Backward-compatibility alias for routers
all_tools: List[BaseTool] = list(LOCAL_TOOLS)

# Central mapping of tool names to category tags
TOOL_METADATA: Dict[str, str] = {
    "syllabus_rag_search": "academic",
    "syllabus_rag_search_async": "academic",
    "web_search_tool": "web_search",
    "study_generator": "study_generation",
}

# Registry mapping tool name -> tool instance
tool_registry: Dict[str, BaseTool] = {
    "syllabus_rag_search": syllabus_rag_search,
    "web_search_tool": web_search_tool,
}

# Router keywords / intent tags for intent classification
tool_categories: Dict[str, List[str]] = {
    "syllabus_rag_search": [
        "syllabus",
        "subject",
        "course",
        "unit",
        "module",
        "credits",
        "semester",
        "objectives",
        "outcomes",
        "topics",
        "curriculum",
        "regulation",
        "cbc",
        "department",
        "lab",
        "practical",
        "theory",
    ],
    "web_search_tool": [
        "latest",
        "current",
        "trend",
        "placement",
        "news",
        "exam",
        "industry",
        "career",
        "job",
        "recruitment",
        "gate",
        "interview",
        "company",
        "salary",
        "package",
    ],
}


def get_all_tools() -> List[BaseTool]:
    """Return the list of active local tools."""
    return list(LOCAL_TOOLS)


def get_tool_registry() -> Dict[str, BaseTool]:
    """Return the local tool registry keyed by name."""
    return dict(tool_registry)


__all__ = [
    "LOCAL_TOOLS",
    "TOOL_METADATA",
    "all_tools",
    "tool_registry",
    "tool_categories",
    "get_all_tools",
    "get_tool_registry",
    "syllabus_rag_search",
    "syllabus_rag_search_async",
    "web_search_tool",
]
