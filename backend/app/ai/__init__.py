"""
app/ai
------
Multi-Agent AI Core — LangGraph Supervisor, LLM Provider Layer & Agent Subgraphs.
"""

from .models import get_llm_with_fallback, get_primary_llm, get_fallback_llm, get_router_llm
from .state import SupervisorState
from .schemas import StudyNotes, QuizDeck, MCQItem, RouteDecision
from .router import Intent, route_query, aroute_query
from .chat_service import ChatService, get_chat_service

__all__ = [
    # LLM providers
    "get_llm_with_fallback",
    "get_primary_llm",
    "get_fallback_llm",
    "get_router_llm",
    # State & Schemas
    "SupervisorState",
    "StudyNotes",
    "QuizDeck",
    "MCQItem",
    "RouteDecision",
    # Router
    "Intent",
    "route_query",
    "aroute_query",
    # Chat Service
    "ChatService",
    "get_chat_service",
]
