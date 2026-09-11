"""
app/ai/agents/mcq/graph.py
-----------------------------
LangGraph subgraph for the MCQ agent.
Flow: retrieve_context → generate_mcqs
"""

from langgraph.graph import StateGraph, START, END

from app.ai.state import SupervisorState
from app.ai.agents.mcq.nodes import retrieve_context, generate_mcqs


def build_mcq_graph() -> StateGraph:
    """
    Build and return the compiled MCQ agent subgraph.

    Graph:
        __start__ → retrieve_context → generate_mcqs → __end__
    """
    graph = StateGraph(SupervisorState)

    # Add nodes
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_mcqs", generate_mcqs)

    # Define edges
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "generate_mcqs")
    graph.add_edge("generate_mcqs", END)

    return graph.compile()


__all__ = ["build_mcq_graph"]
