"""
app/ai/agents/studynotes/nodes/generate.py
---------------------------------------------
Study notes generation node for the StudyNotes agent.
Uses structured output to produce validated StudyNotes.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.models import get_llm_with_fallback
from app.ai.schemas import StudyNotes
from app.ai.state import SupervisorState
from app.ai.agents.studynotes.prompt import STUDYNOTES_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")


async def generate_notes(state: SupervisorState) -> dict:
    """
    Generate structured study notes from the retrieved academic context.

    Attempts structured output (with_structured_output) first.
    Falls back to raw JSON parsing if structured output is not supported
    by the current fallback model.

    Updates:
        state["study_notes"]     — dict of the StudyNotes schema.
        state["final_response"]  — JSON string of the study notes.
    """
    user_query = state.get("user_query", "")
    retrieved_context = state.get("retrieved_context", "")

    if not retrieved_context.strip():
        return {
            "final_response": "No academic content available to generate study notes.",
            "study_notes": None,
        }

    system_prompt = STUDYNOTES_SYSTEM_PROMPT.format(context=retrieved_context)

    llm = get_llm_with_fallback()

    # Attempt 1: Structured output with StudyNotes schema
    try:
        structured_llm = llm.with_structured_output(StudyNotes)
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate comprehensive study notes for: {user_query}"),
        ])

        if isinstance(result, StudyNotes):
            notes_dict = result.model_dump()
        elif isinstance(result, dict):
            notes_dict = StudyNotes.model_validate(result).model_dump()
        else:
            notes_dict = StudyNotes.model_validate(result).model_dump()

        logger.info("[StudyNotesGenerate] Structured output succeeded.")
        return {
            "study_notes": notes_dict,
            "final_response": json.dumps(notes_dict, indent=2, ensure_ascii=False),
        }

    except Exception as exc:
        logger.warning(f"[StudyNotesGenerate] Structured output failed ({exc}); trying raw JSON.")

    # Attempt 2: Raw LLM call + JSON parsing
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Generate comprehensive study notes for: {user_query}\n\n"
                    "Respond ONLY with a valid JSON object matching the StudyNotes schema."
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
        notes = StudyNotes.model_validate(parsed)
        notes_dict = notes.model_dump()

        logger.info("[StudyNotesGenerate] Raw JSON parsing succeeded.")
        return {
            "study_notes": notes_dict,
            "final_response": json.dumps(notes_dict, indent=2, ensure_ascii=False),
        }

    except Exception as exc:
        logger.error(f"[StudyNotesGenerate] All attempts failed: {exc}")
        return {
            "study_notes": None,
            "final_response": f"Failed to generate study notes: {exc}",
        }


__all__ = ["generate_notes"]
