"""
app/routes/voice.py
-------------------
FastAPI router for Voice I/O:
- POST /api/voice/transcribe: Audio transcription via Groq Whisper API
- POST /api/voice/synthesize: Speech synthesis streaming via edge-tts
"""

import io
import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.services.speech_service import (
    DEFAULT_VOICE,
    synthesize_speech,
    synthesize_speech_stream,
    transcribe_audio,
)

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/voice", tags=["voice"])


class SynthesizeRequest(BaseModel):
    text: str = Field(description="Text to convert to speech")
    voice: Optional[str] = Field(default=DEFAULT_VOICE, description="Neural voice identifier")


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(..., description="Audio file to transcribe (wav, mp3, m4a, webm)"),
):
    """
    Transcribe an uploaded audio file using Groq Whisper.
    Returns JSON {"text": "<transcribed text>"}.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file uploaded.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    filename = file.filename or "audio.wav"
    try:
        text = await transcribe_audio(file_bytes=file_bytes, filename=filename)
        return {"text": text}
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"[VoiceRoute] Transcription failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {exc}",
        )


@router.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Convert text to speech and stream back an MP3 audio buffer.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text parameter cannot be empty.",
        )

    voice_name = request.voice or DEFAULT_VOICE
    try:
        return StreamingResponse(
            synthesize_speech_stream(request.text.strip(), voice=voice_name),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "no-cache",
            },
        )
    except Exception as exc:
        logger.error(f"[VoiceRoute] Synthesis failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {exc}",
        )


__all__ = ["router"]
