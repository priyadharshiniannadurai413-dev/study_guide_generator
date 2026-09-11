"""
app/ai/agents/supervisor/nodes/direct_answer.py
-------------------------------------------------
Direct answer node for general knowledge questions and greetings.
Answers from the LLM's own knowledge — no RAG retrieval needed.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.models import get_llm_with_fallback
from app.ai.state import SupervisorState
from app.ai.agents.supervisor.prompt import DIRECT_ANSWER_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")


async def direct_answer_node(state: SupervisorState) -> dict:
    """
    Answer general knowledge questions directly using the LLM's own knowledge.

    No RAG context is retrieved — the LLM responds from its training data.
    Uses the full fallback chain (Mistral Small → Groq → Gemini).

    Updates:
        state["final_response"] — the generated answer.
    """
    user_query = state.get("user_query", "")

    # If the user query contains a web URL, ground the answer strictly on the webpage via Fetch MCP
    from app.ai.context_evaluator import extract_url_from_text
    found_url = extract_url_from_text(user_query)
    if found_url:
        try:
            from app.ai.web_content_service import get_web_content_service
            web_service = get_web_content_service()
            web_result = await web_service.answer_question_from_web(url=found_url, question=user_query)
            if web_result.get("success"):
                answer = web_result.get("answer", "")
                source_meta = web_result.get("source", {})
                source_str = f"\n\n**Source**: [{source_meta.get('title', 'Web Document')}]({source_meta.get('url', found_url)})"
                return {
                    "final_response": f"{answer}{source_str}",
                    "web_sources": [source_meta],
                }
        except Exception as web_exc:
            logger.warning(f"[DirectAnswer] Web answer extraction notice: {web_exc}; falling back to general LLM")

    llm = get_llm_with_fallback()

    try:
        response = await llm.ainvoke([
            SystemMessage(content=DIRECT_ANSWER_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ])

        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )

        final_text = str(content).strip()
        logger.info(f"[DirectAnswer] Generated response ({len(final_text)} chars).")
        return {"final_response": final_text}

    except Exception as exc:
        logger.error(f"[DirectAnswer] All LLM providers failed: {exc}")
        return {
            "final_response": (
                "I'm sorry, I couldn't process your question right now. "
                "Please try again in a moment."
            )
        }


__all__ = ["direct_answer_node"]
