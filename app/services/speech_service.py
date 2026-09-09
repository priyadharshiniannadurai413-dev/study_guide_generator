"""
app/services/speech_service.py
------------------------------
Voice I/O subsystem:
- Speech-to-Text (STT): Groq Whisper API (whisper-large-v3)
- Text-to-Speech (TTS): Microsoft Edge TTS (edge-tts)
"""

import asyncio
import io
import logging
from typing import AsyncGenerator, Optional

import edge_tts
from app.core.config import settings

logger = logging.getLogger("uvicorn")

DEFAULT_VOICE = "en-US-JennyNeural"
GROQ_WHISPER_MODEL = "whisper-large-v3"


async def transcribe_audio(
    file_bytes: bytes,
    filename: str = "audio.wav",
) -> str:
    """
    Transcribe raw audio bytes using Groq Whisper API.

    Args:
        file_bytes: Raw bytes of uploaded audio (wav, mp3, m4a, webm).
        filename: Name of the uploaded file.

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If file_bytes is empty or GROQ_API_KEY is not configured.
        RuntimeError: If transcription API call fails.
    """
    if not file_bytes:
        raise ValueError("Audio file is empty.")

    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        logger.warning("[SpeechService] GROQ_API_KEY is not configured.")
        # Fallback informative transcription notice
        return "GROQ_API_KEY is not configured on the server. Please configure it to enable audio transcription."

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)
        audio_file = (filename, file_bytes)

        transcription = await client.audio.transcriptions.create(
            file=audio_file,
            model=GROQ_WHISPER_MODEL,
            response_format="text",
        )
        return str(transcription).strip()
    except Exception as exc:
        logger.error(f"[SpeechService] Groq Whisper transcription failed: {exc}")
        raise RuntimeError(f"Transcription failed: {exc}") from exc


async def synthesize_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
) -> bytes:
    """
    Synthesize text into MP3 audio bytes using edge-tts.

    Args:
        text: Text to speak.
        voice: Neural voice name (default: en-US-JennyNeural).

    Returns:
        MP3 audio bytes.
    """
    if not text or not text.strip():
        raise ValueError("Text to synthesize cannot be empty.")

    communicate = edge_tts.Communicate(text.strip(), voice)
    audio_buffer = io.BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    return audio_buffer.getvalue()


async def synthesize_speech_stream(
    text: str,
    voice: str = DEFAULT_VOICE,
) -> AsyncGenerator[bytes, None]:
    """
    Asynchronous generator yielding audio chunks for StreamingResponse.
    """
    if not text or not text.strip():
        return

    communicate = edge_tts.Communicate(text.strip(), voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


__all__ = [
    "transcribe_audio",
    "synthesize_speech",
    "synthesize_speech_stream",
    "DEFAULT_VOICE",
]
