"""
Text-to-Speech via OpenAI TTS API.

Returns MP3 bytes for the given text.
Supports voices: alloy, echo, fable, onyx, nova, shimmer.
~$0.015 per 1K characters (tts-1), ~$0.030 (tts-1-hd).
"""

from __future__ import annotations

import logging
import os

import openai

log = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TTS_MODEL      = os.getenv("TTS_MODEL", "tts-1")          # tts-1 or tts-1-hd
TTS_VOICE      = os.getenv("TTS_VOICE", "nova")           # alloy|echo|fable|onyx|nova|shimmer
TTS_MAX_CHARS  = 4096                                      # OpenAI limit per request


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """
    Convert *text* to MP3 audio bytes using OpenAI TTS.

    Parameters
    ----------
    text  : plain text to speak (max 4096 chars per call)
    voice : override the default TTS_VOICE

    Returns
    -------
    Raw MP3 bytes, or raises ValueError on failure.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set — cannot synthesize speech")

    if len(text) > TTS_MAX_CHARS:
        text = text[:TTS_MAX_CHARS]
        log.warning("TTS input truncated to %d characters", TTS_MAX_CHARS)

    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

    try:
        response = await client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice or TTS_VOICE,
            input=text,
            response_format="mp3",
        )
        audio_bytes = response.content
        log.info("TTS synthesized %d chars → %d bytes MP3", len(text), len(audio_bytes))
        return audio_bytes
    except openai.OpenAIError as exc:
        log.error("OpenAI TTS error: %s", exc)
        raise ValueError(f"Speech synthesis failed: {exc}") from exc
