"""
app/ai/agents/mcq/graph.py
-----------------------------
LangGraph subgraph for the MCQ agent with Fetch MCP enrichment.

Flow:
    START → retrieve_context → evaluate_context
              │
              ├── [route: "generate"] ──→ generate_mcqs ──→ END
              │
              └── [route: "fetch_web"] ─→ fetch_web → validate_web → generate_mcqs ──→ END
"""

from langgraph.graph import StateGraph, START, END

from app.ai.state import SupervisorState
from app.ai.agents.mcq.nodes import retrieve_context, generate_mcqs
from app.ai.context_evaluator import (
    evaluate_context_node,
    route_after_evaluation,
    fetch_web_node,
    validate_web_node,
)


def build_mcq_graph() -> StateGraph:
    """Build and return the compiled MCQ agent subgraph with Fetch MCP."""
    graph = StateGraph(SupervisorState)

    # Nodes
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("evaluate_context", evaluate_context_node)
    graph.add_node("fetch_web", fetch_web_node)
    graph.add_node("validate_web", validate_web_node)
    graph.add_node("generate_mcqs", generate_mcqs)

    # Edges
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "evaluate_context")

    # Conditional routing
    graph.add_conditional_edges(
        "evaluate_context",
        route_after_evaluation,
        {
            "generate": "generate_mcqs",
            "fetch_web": "fetch_web",
        },
    )

    # Web enrichment
    graph.add_edge("fetch_web", "validate_web")
    graph.add_edge("validate_web", "generate_mcqs")

    # Exit
    graph.add_edge("generate_mcqs", END)

    return graph.compile()


__all__ = ["build_mcq_graph"]
