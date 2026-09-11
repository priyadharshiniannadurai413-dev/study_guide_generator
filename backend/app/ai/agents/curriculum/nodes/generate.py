"""
app/ai/agents/curriculum/nodes/generate.py
---------------------------------------------
Answer generation node for the Curriculum agent.
Takes RAG-retrieved context and generates a grounded answer
using the full LLM fallback chain.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.models import get_llm_with_fallback
from app.ai.state import SupervisorState
from app.ai.agents.curriculum.prompt import CURRICULUM_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")


async def generate_answer(state: SupervisorState) -> dict:
    """
    Generate a RAG-grounded answer to the user's curriculum question.

    Uses the retrieved context injected into the system prompt and
    invokes the LLM with the full fallback chain
    (Mistral Small → Groq gpt-oss-20b → Gemini).

    Updates:
        state["final_response"] — the generated answer.
    """
    user_query = state.get("user_query", "")
    retrieved_context = state.get("retrieved_context", "")

    # Build the system prompt with injected context
    system_prompt = CURRICULUM_SYSTEM_PROMPT.format(context=retrieved_context)

    llm = get_llm_with_fallback()

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query),
        ])

        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )

        final_text = str(content).strip()
        logger.info(f"[CurriculumGenerate] Generated answer ({len(final_text)} chars).")
        return {"final_response": final_text}

    except Exception as exc:
        logger.error(f"[CurriculumGenerate] All LLM providers failed: {exc}")
        return {
            "final_response": (
                "I'm sorry, I couldn't generate an answer right now. "
                "Please try again in a moment."
            )
        }


__all__ = ["generate_answer"]
