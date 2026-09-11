"""
app/ai/agents/curriculum/graph.py
-----------------------------------
LangGraph subgraph for the Curriculum agent.
Flow: retrieve_context → generate_answer
"""

from langgraph.graph import StateGraph, START, END

from app.ai.state import SupervisorState
from app.ai.agents.curriculum.nodes import retrieve_context, generate_answer


def build_curriculum_graph() -> StateGraph:
    """
    Build and return the compiled Curriculum agent subgraph.

    Graph:
        __start__ → retrieve_context → generate_answer → __end__
    """
    graph = StateGraph(SupervisorState)

    # Add nodes
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_answer", generate_answer)

    # Define edges
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


__all__ = ["build_curriculum_graph"]
