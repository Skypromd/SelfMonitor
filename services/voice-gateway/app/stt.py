"""
Speech-to-Text via OpenAI Whisper API.

Accepts raw audio bytes (webm/mp4/wav/mp3) and returns transcribed text.
~$0.006 per minute of audio.
"""

from __future__ import annotations

import io
import logging
import os

import openai

log = logging.getLogger(__name__)

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "whisper-1")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")   # set "ru" for Russian


async def transcribe(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
) -> str:
    """
    Transcribe *audio_bytes* using OpenAI Whisper.

    Parameters
    ----------
    audio_bytes : raw audio (webm, mp4, wav, mp3, ogg, flac, m4a — max 25 MB)
    filename    : hint for the file format (extension matters)
    language    : ISO-639-1 code; None = auto-detect

    Returns
    -------
    Transcribed text string, or raises ValueError on failure.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set — cannot transcribe audio")

    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename          # OpenAI SDK reads .name for MIME type

    try:
        response = await client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
            language=language or WHISPER_LANGUAGE,
            response_format="text",
        )
        text = str(response).strip()
        log.info("Whisper transcribed %d bytes → %d chars", len(audio_bytes), len(text))
        return text
    except openai.OpenAIError as exc:
        log.error("Whisper STT error: %s", exc)
        raise ValueError(f"Transcription failed: {exc}") from exc
