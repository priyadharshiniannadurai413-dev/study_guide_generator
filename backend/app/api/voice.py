"""
app/api/voice.py
----------------
Alias exposing the voice router from app.routes.voice.
"""

from app.routes.voice import router

__all__ = ["router"]
