"""
app/ai/chat_service.py
----------------------
LangGraph-powered chat service.
Replaces the legacy manual tool-binding loop with the compiled
Supervisor graph for intent routing and agent execution.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.ai.agents.supervisor.graph import get_supervisor_graph

logger = logging.getLogger("uvicorn")


class ChatService:
    """
    LangGraph-driven chat coordinator.
    Invokes the compiled Supervisor graph which handles:
    - Intent classification (router node)
    - Routing to specialist agents (curriculum, studynotes, mcq)
    - Direct answers for general knowledge
    - RAG retrieval and LLM generation with fallbacks
    """

    def __init__(self):
        self._graph = get_supervisor_graph()

    async def invoke(
        self,
        user_prompt: str,
        user_id: str = "anonymous",
        doc_id: str = "syllabus",
        num_questions: int = 5,
        conversation_history: Optional[List[dict]] = None,
        route: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke the full Supervisor graph and return the result state.

        Args:
            user_prompt:          The user's question or request.
            user_id:              Authenticated user ID (optional, defaults to "anonymous").
            doc_id:               Document scope — "syllabus" or user doc UUID.
            num_questions:        Number of MCQs to generate (only used by mcq agent).
            conversation_history: Prior conversation turns.
            route:                Optional explicit agent route (e.g. 'study_notes', 'mcq').

        Returns:
            Final graph state dict containing final_response, study_notes, quiz_deck, etc.
        """
        # Build initial state
        initial_state = {
            "messages": [],
            "user_query": user_prompt.strip(),
            "user_id": user_id,
            "doc_id": doc_id,
            "route": route or "",
            "retrieved_context": "",
            "final_response": "",
            "study_notes": None,
            "quiz_deck": None,
            "num_questions": num_questions,
        }

        logger.info(
            f"[ChatService] Invoking graph — user_id={user_id}, "
            f"doc_id={doc_id}, query={user_prompt[:80]}..."
        )

        result = await self._graph.ainvoke(initial_state)

        logger.info(
            f"[ChatService] Graph completed — route={result.get('route')}, "
            f"response_len={len(result.get('final_response', ''))}"
        )

        return result

    async def stream_tokens(
        self,
        user_prompt: str,
        user_id: str = "anonymous",
        doc_id: str = "syllabus",
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Execute the Supervisor graph and yield the final response as a
        single token chunk. For true token-level streaming, a future
        version can use graph.astream_events().

        Yields:
            Text chunks of the final response.
        """
        try:
            result = await self.invoke(
                user_prompt=user_prompt,
                user_id=user_id,
                doc_id=doc_id,
                conversation_history=conversation_history,
            )

            final_response = result.get("final_response", "")
            if final_response:
                yield final_response
            else:
                yield "I couldn't generate a response. Please try again."

        except Exception as exc:
            logger.error(f"[ChatService] Graph invocation failed: {exc}")
            yield f"An error occurred: {exc}"

    async def stream_response(
        self,
        user_prompt: str,
        user_id: str = "anonymous",
        doc_id: str = "syllabus",
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Yield SSE-formatted event data chunks: `data: {"text": "..."}\\n\\n`
        followed by `data: [DONE]\\n\\n` on completion.
        """
        try:
            async for token in self.stream_tokens(
                user_prompt, user_id, doc_id, conversation_history
            ):
                payload = json.dumps({"text": token})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.error(f"[ChatService] Error in stream_response: {exc}")
            err_payload = json.dumps({"error": f"Stream error: {exc}"})
            yield f"data: {err_payload}\n\n"
        finally:
            yield "data: [DONE]\n\n"


_chat_service_instance: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Return singleton ChatService instance."""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    return _chat_service_instance


__all__ = ["ChatService", "get_chat_service"]
