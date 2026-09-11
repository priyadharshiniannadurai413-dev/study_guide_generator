"""
app/ai/agents/supervisor/graph.py
------------------------------------
Main Supervisor LangGraph — the entry point for all user queries.
Routes to specialist agent subgraphs via conditional edges.

Architecture:
    __start__ → router_node → [conditional edge] → {
        "curriculum":    curriculum_subgraph,
        "study_notes":   studynotes_subgraph,
        "mcq":           mcq_subgraph,
        "direct_answer": direct_answer_node,
    } → finalize_response → __end__
"""

import logging

from langgraph.graph import StateGraph, START, END

from app.ai.state import SupervisorState
from app.ai.agents.supervisor.nodes import (
    router_node,
    direct_answer_node,
    finalize_response,
)
from app.ai.agents.curriculum.graph import build_curriculum_graph
from app.ai.agents.studynotes.graph import build_studynotes_graph
from app.ai.agents.mcq.graph import build_mcq_graph

logger = logging.getLogger("uvicorn")


def _route_decision(state: SupervisorState) -> str:
    """
    Conditional edge function — reads the classified route from state
    and returns the target node name for the graph to execute.
    """
    route = state.get("route", "direct_answer")
    if route not in {"curriculum", "study_notes", "mcq", "direct_answer"}:
        logger.warning(f"[Supervisor] Unknown route '{route}' — defaulting to direct_answer.")
        return "direct_answer"
    return route


def build_supervisor_graph():
    """
    Build and compile the full Supervisor LangGraph.

    Returns:
        Compiled LangGraph ready for invocation via .ainvoke() or .astream().
    """
    graph = StateGraph(SupervisorState)

    # ── Register nodes ────────────────────────────────────────────────────
    graph.add_node("router_node", router_node)
    graph.add_node("direct_answer", direct_answer_node)
    graph.add_node("finalize_response", finalize_response)

    # Register subgraph agents as nodes
    graph.add_node("curriculum", build_curriculum_graph())
    graph.add_node("study_notes", build_studynotes_graph())
    graph.add_node("mcq", build_mcq_graph())

    # ── Define edges ──────────────────────────────────────────────────────
    # Entry: start → router
    graph.add_edge(START, "router_node")

    # Conditional: router → specialist agent
    graph.add_conditional_edges(
        "router_node",
        _route_decision,
        {
            "curriculum": "curriculum",
            "study_notes": "study_notes",
            "mcq": "mcq",
            "direct_answer": "direct_answer",
        },
    )

    # All agents → finalizer → end
    graph.add_edge("curriculum", "finalize_response")
    graph.add_edge("study_notes", "finalize_response")
    graph.add_edge("mcq", "finalize_response")
    graph.add_edge("direct_answer", "finalize_response")
    graph.add_edge("finalize_response", END)

    compiled = graph.compile()
    logger.info("[Supervisor] Graph compiled successfully.")

    return compiled


# Pre-built singleton for import convenience
_supervisor_graph = None


def get_supervisor_graph():
    """Return a cached compiled supervisor graph instance."""
    global _supervisor_graph
    if _supervisor_graph is None:
        _supervisor_graph = build_supervisor_graph()
    return _supervisor_graph


__all__ = ["build_supervisor_graph", "get_supervisor_graph"]
