"""
app/routes/llm.py
-----------------
Chatbot & streaming execution routes.
Invokes the LangGraph-powered ChatService for SSE token streaming.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.ai.chat_service import get_chat_service
from app.auth.dependencies import get_current_user

logger = logging.getLogger("uvicorn")

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    user_prompt: str = Field(..., description="Message from student")
    doc_id: str = Field(default="syllabus", description="Document scope — 'syllabus' or user doc UUID")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Prior conversation history e.g. [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]",
    )


@router.post("/api/chat/stream")
@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Real-time Server-Sent Events (SSE) streaming chat endpoint.
    Protected by Clerk authentication.
    Routes through the LangGraph Supervisor for intelligent agent dispatch.
    """
    if not request.user_prompt or not request.user_prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_prompt cannot be empty.",
        )

    user_id = current_user.get("sub", "anonymous")

    chat_service = get_chat_service()
    event_stream = chat_service.stream_response(
        user_prompt=request.user_prompt.strip(),
        user_id=user_id,
        doc_id=request.doc_id,
        conversation_history=request.conversation_history,
    )

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chatbot")
async def chatbot(request: ChatRequest):
    """Legacy backward-compatible health/echo endpoint."""
    if not request.user_prompt or not request.user_prompt.strip():
        return JSONResponse(
            status_code=422,
            content={
                "error": "user_prompt cannot be empty.",
                "example": {"user_prompt": "Explain Chapter 1 concepts"},
            },
        )

    return {
        "status": "ok",
        "service": "ai-study-assistant",
        "user_prompt": request.user_prompt,
        "message": "Chat endpoint ready. Use /api/chat/stream for streaming responses.",
    }


__all__ = ["router"]
