"""
app/ai/agents/supervisor/nodes/router.py
------------------------------------------
Intent classification node for the Supervisor graph.
Uses a lightweight LLM (Gemini flash-lite) with structured output
to classify the user query into one of the specialist agent routes.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.models import get_router_llm
from app.ai.schemas import RouteDecision
from app.ai.state import SupervisorState
from app.ai.agents.supervisor.prompt import ROUTER_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")

# Valid route values
VALID_ROUTES = {"curriculum", "study_notes", "mcq", "direct_answer"}


async def router_node(state: SupervisorState) -> dict:
    """
    Classify user intent and set the routing decision.

    1. Checks if explicit valid route is already specified in state.
    2. Attempts structured output (RouteDecision schema) via router LLM.
    3. Falls back to raw text parsing.
    4. Falls back to keyword heuristics before defaulting to direct_answer.

    Updates:
        state["route"] — one of: curriculum, study_notes, mcq, direct_answer
    """
    # 1. Check if caller already provided an explicit route
    existing_route = state.get("route", "")
    if existing_route and existing_route in VALID_ROUTES:
        logger.info(f"[Router] Using explicitly requested route → {existing_route}")
        return {"route": existing_route}

    user_query = state.get("user_query", "")

    if not user_query.strip():
        logger.info("[Router] Empty query — routing to direct_answer (greeting).")
        return {"route": "direct_answer"}

    llm = get_router_llm()

    # Attempt 1: Structured output with RouteDecision schema
    try:
        structured_llm = llm.with_structured_output(RouteDecision)
        result = await structured_llm.ainvoke([
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ])

        if isinstance(result, RouteDecision) and result.route in VALID_ROUTES:
            logger.info(f"[Router] Structured classification → {result.route}")
            return {"route": result.route}

    except Exception as exc:
        logger.debug(f"[Router] Structured output failed ({exc}); trying raw text.")

    # Attempt 2: Raw text classification
    try:
        response = await llm.ainvoke([
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ])
        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        raw_text = str(content).strip().lower()

        for route in VALID_ROUTES:
            if route in raw_text:
                logger.info(f"[Router] Text classification → {route}")
                return {"route": route}

    except Exception as exc:
        logger.warning(f"[Router] LLM classification failed ({exc}); trying keyword heuristics.")

    # Attempt 3: Keyword / intent heuristics
    query_lower = user_query.lower()
    if any(k in query_lower for k in ["study note", "study notes", "notes for", "summarize notes", "generate notes", "create notes"]):
        logger.info("[Router] Keyword heuristic → study_notes")
        return {"route": "study_notes"}

    if any(k in query_lower for k in ["mcq", "quiz", "multiple choice", "questions for", "practice questions"]):
        logger.info("[Router] Keyword heuristic → mcq")
        return {"route": "mcq"}

    doc_id = state.get("doc_id", "")
    if doc_id and doc_id != "syllabus":
        logger.info("[Router] Document scope heuristic → curriculum")
        return {"route": "curriculum"}

    # Default fallback
    logger.info("[Router] Could not classify — defaulting to direct_answer.")
    return {"route": "direct_answer"}


__all__ = ["router_node"]
