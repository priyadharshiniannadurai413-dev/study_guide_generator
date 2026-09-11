"""
app/ai/state.py
----------------
Top-level shared state definition for the LangGraph multi-agent workflow.
All agent subgraphs operate on this same TypedDict so data flows cleanly
between the Supervisor router and each specialist agent.
"""

from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class SupervisorState(TypedDict):
    """
    Shared state flowing through the entire Supervisor → Agent subgraph pipeline.

    Fields:
        messages:           LangChain message history with automatic deduplication.
        user_query:         The raw user question / prompt.
        user_id:            Authenticated user identifier (optional, defaults to "anonymous").
        doc_id:             Document scope — "syllabus" for global RAG, or a user doc UUID.
        route:              Classified intent: curriculum | study_notes | mcq | direct_answer.
        retrieved_context:  Formatted RAG retrieval results as text for the LLM.
        final_response:     The final answer string to return to the user.
        study_notes:        Structured study notes dict (populated when route=study_notes).
        quiz_deck:          Structured MCQ quiz dict (populated when route=mcq).
        num_questions:      Number of MCQs to generate (default 5, only used by mcq agent).
    """

    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str
    user_id: str
    doc_id: str
    route: str
    retrieved_context: str
    final_response: str
    study_notes: Optional[Dict[str, Any]]
    quiz_deck: Optional[Dict[str, Any]]
    num_questions: int
    # ── Fetch MCP & Evidence Enrichment ───────────────────────────────
    rag_context: Optional[str]
    rag_sources: Optional[List[Dict[str, Any]]]
    web_context: Optional[str]
    web_sources: Optional[List[Dict[str, Any]]]
    combined_context: Optional[str]
    enable_web: Optional[bool]
    web_target_url: Optional[str]
    web_fetch_error: Optional[str]
    web_sufficiency_score: Optional[float]


__all__ = ["SupervisorState"]
