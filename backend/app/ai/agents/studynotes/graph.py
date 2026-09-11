"""
app/ai/agents/studynotes/graph.py
-----------------------------------
LangGraph subgraph for the StudyNotes agent.
Flow: retrieve_context → generate_notes
"""

from langgraph.graph import StateGraph, START, END

from app.ai.state import SupervisorState
from app.ai.agents.studynotes.nodes import retrieve_context, generate_notes


def build_studynotes_graph() -> StateGraph:
    """
    Build and return the compiled StudyNotes agent subgraph.

    Graph:
        __start__ → retrieve_context → generate_notes → __end__
    """
    graph = StateGraph(SupervisorState)

    # Add nodes
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_notes", generate_notes)

    # Define edges
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "generate_notes")
    graph.add_edge("generate_notes", END)

    return graph.compile()


__all__ = ["build_studynotes_graph"]
