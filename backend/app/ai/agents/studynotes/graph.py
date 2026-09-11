"""
app/ai/agents/studynotes/graph.py
-----------------------------------
LangGraph subgraph for the StudyNotes agent with Fetch MCP enrichment.

Flow:
    START → retrieve_context → evaluate_context
              │
              ├── [route: "generate"] ──→ generate_notes ──→ END
              │
              └── [route: "fetch_web"] ─→ fetch_web → validate_web → generate_notes ──→ END
"""

from langgraph.graph import StateGraph, START, END

from app.ai.state import SupervisorState
from app.ai.agents.studynotes.nodes import retrieve_context, generate_notes
from app.ai.context_evaluator import (
    evaluate_context_node,
    route_after_evaluation,
    fetch_web_node,
    validate_web_node,
)


def build_studynotes_graph() -> StateGraph:
    """Build and return the compiled StudyNotes agent subgraph with Fetch MCP."""
    graph = StateGraph(SupervisorState)

    # Core nodes
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("evaluate_context", evaluate_context_node)
    graph.add_node("fetch_web", fetch_web_node)
    graph.add_node("validate_web", validate_web_node)
    graph.add_node("generate_notes", generate_notes)

    # Edges
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "evaluate_context")

    # Conditional routing after sufficiency check
    graph.add_conditional_edges(
        "evaluate_context",
        route_after_evaluation,
        {
            "generate": "generate_notes",
            "fetch_web": "fetch_web",
        },
    )

    # Web enrichment pipeline
    graph.add_edge("fetch_web", "validate_web")
    graph.add_edge("validate_web", "generate_notes")

    # Exit
    graph.add_edge("generate_notes", END)

    return graph.compile()


__all__ = ["build_studynotes_graph"]
