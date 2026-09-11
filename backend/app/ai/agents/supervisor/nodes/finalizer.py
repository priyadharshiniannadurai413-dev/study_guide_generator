"""
app/ai/agents/supervisor/nodes/finalizer.py
----------------------------------------------
Response finalizer node — ensures the final output is properly
formatted before returning from the graph.
"""

import json
import logging

from app.ai.state import SupervisorState

logger = logging.getLogger("uvicorn")


async def finalize_response(state: SupervisorState) -> dict:
    """
    Finalize the response before returning from the graph.

    If structured data (study_notes or quiz_deck) was produced,
    serializes it into the final_response as JSON.
    Otherwise, passes through the text final_response as-is.

    Updates:
        state["final_response"] — guaranteed to be a non-empty string.
    """
    route = state.get("route", "")
    final_response = state.get("final_response", "")
    study_notes = state.get("study_notes")
    quiz_deck = state.get("quiz_deck")

    # If structured data exists but final_response is empty, serialize it
    if not final_response and study_notes:
        final_response = json.dumps(study_notes, indent=2, ensure_ascii=False)
        logger.info("[Finalizer] Serialized study_notes into final_response.")

    elif not final_response and quiz_deck:
        final_response = json.dumps(quiz_deck, indent=2, ensure_ascii=False)
        logger.info("[Finalizer] Serialized quiz_deck into final_response.")

    # Absolute fallback
    if not final_response:
        final_response = (
            "I couldn't generate a response for your query. "
            "Please try rephrasing your question."
        )
        logger.warning("[Finalizer] No response produced — returning fallback message.")

    logger.info(f"[Finalizer] Route: {route} | Response length: {len(final_response)} chars")

    return {"final_response": final_response}


__all__ = ["finalize_response"]
