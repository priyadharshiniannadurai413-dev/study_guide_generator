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


class DirectMessageRequest(BaseModel):
    message: Optional[str] = Field(default=None, description="Query prompt from client")
    user_prompt: Optional[str] = Field(default=None, description="Alias for message")
    doc_id: str = Field(default="syllabus", description="Document scope")
    route: Optional[str] = Field(default=None, description="Explicit route target e.g. 'github'")
    enable_web: bool = Field(default=False, description="Enable Fetch MCP web enrichment")


@router.post("/api/chat/message")
@router.post("/chat/message")
async def chat_message(
    request: DirectMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Direct synchronous message execution endpoint for the GitHub Workbench and API clients.
    """
    query = (request.message or request.user_prompt or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    user_id = current_user.get("sub", "anonymous")
    chat_service = get_chat_service()
    result = await chat_service.invoke(
        user_prompt=query,
        user_id=user_id,
        doc_id=request.doc_id,
        route=request.route,
        enable_web=request.enable_web,
    )

    final_resp = result.get("final_response") or "Operation completed."
    return {
        "response": final_resp,
        "text": final_resp,
        "route": result.get("route"),
        "sources": {
            "rag": [request.doc_id],
            "web": result.get("web_sources", []),
        },
    }


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
