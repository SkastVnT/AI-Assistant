"""
Audio Transcription Integration for Chatbot
Provides speech-to-text via OpenAI Whisper API or local Whisper model.
Supports: mp3, wav, m4a, flac, ogg, webm
"""

import os
import io
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm', '.wma', '.aac'}
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB (OpenAI Whisper limit)


def is_audio_file(filename: str) -> bool:
    """Check if a file is an audio file by extension."""
    return Path(filename).suffix.lower() in AUDIO_EXTENSIONS


def transcribe_audio(audio_data: bytes, filename: str, language: str = "vi") -> Dict[str, Any]:
    """
    Transcribe audio to text using available backends.

    Priority:
    1. OpenAI Whisper API (cloud, fast, accurate)
    2. Groq Whisper API (fast, free tier)
    3. Return error if no backend available

    Args:
        audio_data: Raw audio bytes
        filename: Original filename (for extension detection)
        language: Language hint (default: Vietnamese)

    Returns:
        Dict with keys: success, text, duration_seconds, method, error
    """
    result = {
        "success": False,
        "text": "",
        "duration_seconds": 0,
        "method": "none",
        "error": None,
    }

    if len(audio_data) > MAX_AUDIO_SIZE:
        result["error"] = f"Audio file too large ({len(audio_data) // 1024 // 1024}MB). Max: 25MB"
        return result

    # Try OpenAI Whisper API
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            return _transcribe_openai(audio_data, filename, language, openai_key)
        except Exception as e:
            logger.warning(f"[STT] OpenAI Whisper failed: {e}")

    # Try Groq Whisper API (free, fast)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            return _transcribe_groq(audio_data, filename, language, groq_key)
        except Exception as e:
            logger.warning(f"[STT] Groq Whisper failed: {e}")

    # Try Grok/xAI (if they support audio - currently text only, skip)

    result["error"] = "No speech-to-text API key available. Set OPENAI_API_KEY or GROQ_API_KEY."
    return result


def _transcribe_openai(
    audio_data: bytes, filename: str, language: str, api_key: str
) -> Dict[str, Any]:
    """Transcribe using OpenAI Whisper API."""
    import openai

    client = openai.OpenAI(api_key=api_key)

    # Write to temp file (API requires file-like object with name)
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language if language != "auto" else None,
                response_format="verbose_json",
            )

        return {
            "success": True,
            "text": transcript.text,
            "duration_seconds": getattr(transcript, "duration", 0),
            "method": "openai_whisper",
            "error": None,
        }
    finally:
        os.unlink(tmp_path)


def _transcribe_groq(
    audio_data: bytes, filename: str, language: str, api_key: str
) -> Dict[str, Any]:
    """Transcribe using Groq Whisper API (free tier)."""
    import requests

    suffix = Path(filename).suffix or ".wav"
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/m4a",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
    }
    mime_type = mime_map.get(suffix.lower(), "audio/wav")

    response = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": (filename, audio_data, mime_type)},
        data={
            "model": "whisper-large-v3",
            "language": language if language != "auto" else "",
            "response_format": "verbose_json",
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "success": True,
        "text": data.get("text", ""),
        "duration_seconds": data.get("duration", 0),
        "method": "groq_whisper",
        "error": None,
    }
