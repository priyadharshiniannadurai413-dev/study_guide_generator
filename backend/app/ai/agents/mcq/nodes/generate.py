"""
app/ai/agents/mcq/nodes/generate.py
---------------------------------------
MCQ quiz generation node for the MCQ agent.
Uses structured output to produce validated QuizDeck.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.models import get_llm_with_fallback
from app.ai.schemas import QuizDeck
from app.ai.state import SupervisorState
from app.ai.agents.mcq.prompt import MCQ_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")


async def generate_mcqs(state: SupervisorState) -> dict:
    """
    Generate a structured MCQ quiz from the retrieved academic context.

    Attempts structured output (with_structured_output) first.
    Falls back to raw JSON parsing if structured output is not supported
    by the current fallback model.

    Updates:
        state["quiz_deck"]      — dict of the QuizDeck schema.
        state["final_response"] — JSON string of the quiz deck.
    """
    user_query = state.get("user_query", "")
    retrieved_context = state.get("retrieved_context", "")
    num_questions = state.get("num_questions", 5)

    if not retrieved_context.strip():
        return {
            "final_response": "No academic content available to generate MCQs.",
            "quiz_deck": None,
        }

    system_prompt = MCQ_SYSTEM_PROMPT.format(
        context=retrieved_context,
        num_questions=num_questions,
    )

    llm = get_llm_with_fallback()

    # Attempt 1: Structured output with QuizDeck schema
    try:
        structured_llm = llm.with_structured_output(QuizDeck)
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Generate exactly {num_questions} multiple-choice questions "
                    f"based on: {user_query}"
                )
            ),
        ])

        if isinstance(result, QuizDeck):
            quiz_dict = result.model_dump()
        elif isinstance(result, dict):
            quiz_dict = QuizDeck.model_validate(result).model_dump()
        else:
            quiz_dict = QuizDeck.model_validate(result).model_dump()

        logger.info(
            f"[MCQGenerate] Structured output succeeded — "
            f"{len(quiz_dict.get('questions', []))} questions."
        )
        return {
            "quiz_deck": quiz_dict,
            "final_response": json.dumps(quiz_dict, indent=2, ensure_ascii=False),
        }

    except Exception as exc:
        logger.warning(f"[MCQGenerate] Structured output failed ({exc}); trying raw JSON.")

    # Attempt 2: Raw LLM call + JSON parsing
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Generate exactly {num_questions} MCQs for: {user_query}\n\n"
                    "Respond ONLY with a valid JSON object matching the QuizDeck schema."
                )
            ),
        ])

        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        content = str(content).strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if content.startswith("json"):
            content = content[4:].strip()

        parsed = json.loads(content)
        quiz = QuizDeck.model_validate(parsed)
        quiz_dict = quiz.model_dump()

        logger.info(
            f"[MCQGenerate] Raw JSON parsing succeeded — "
            f"{len(quiz_dict.get('questions', []))} questions."
        )
        return {
            "quiz_deck": quiz_dict,
            "final_response": json.dumps(quiz_dict, indent=2, ensure_ascii=False),
        }

    except Exception as exc:
        logger.error(f"[MCQGenerate] All attempts failed: {exc}")
        return {
            "quiz_deck": None,
            "final_response": f"Failed to generate MCQ quiz: {exc}",
        }


__all__ = ["generate_mcqs"]
