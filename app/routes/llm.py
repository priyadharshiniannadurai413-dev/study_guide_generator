from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class ChatRequest(BaseModel):
    user_prompt: str
    conversation_history: Optional[List[dict]] = None


@router.post("/chatbot")
async def chatbot(request: ChatRequest):
    # Validate that user_prompt is not empty or whitespace-only
    if not request.user_prompt or not request.user_prompt.strip():
        return JSONResponse(
            status_code=422,
            content={
                "error": "user_prompt cannot be empty.",
                "example": {"user_prompt": "Explain Chapter 1 concepts"}
            }
        )

    return {
        "status": "ok",
        "service": "ai-study-assistant",
        "user_prompt": request.user_prompt,
        "message": "Chat endpoint ready."
    }
