"""Tests for Voice Gateway service."""

import base64
import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-voice-gw")
os.environ.setdefault("OPENAI_API_KEY",  "test-key")


# ── STT unit tests ────────────────────────────────────────────────────────────

from app.stt import transcribe


@pytest.mark.asyncio
async def test_transcribe_no_api_key():
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        import importlib

        import app.stt as stt_module
        stt_module.OPENAI_API_KEY = ""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await transcribe(b"fake audio", language="en")
    # restore
    import app.stt as stt_module
    stt_module.OPENAI_API_KEY = "test-key"


@pytest.mark.asyncio
async def test_transcribe_calls_openai():
    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value="Hello world")

    with patch("app.stt.openai.AsyncOpenAI", return_value=mock_client):
        result = await transcribe(b"audio data", filename="test.webm", language="en")
    assert result == "Hello world"


# ── TTS unit tests ────────────────────────────────────────────────────────────

from app.tts import synthesize


@pytest.mark.asyncio
async def test_synthesize_no_api_key():
    import app.tts as tts_module
    original = tts_module.OPENAI_API_KEY
    tts_module.OPENAI_API_KEY = ""
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        await synthesize("Hello")
    tts_module.OPENAI_API_KEY = original


@pytest.mark.asyncio
async def test_synthesize_calls_openai():
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.content = b"mp3 data"

    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(return_value=mock_response)

    with patch("app.tts.openai.AsyncOpenAI", return_value=mock_client):
        audio = await synthesize("Hello there")
    assert audio == b"mp3 data"


@pytest.mark.asyncio
async def test_synthesize_truncates_long_text():
    """Text longer than 4096 chars must be truncated (checked via mock)."""
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.content = b"truncated audio"
    mock_client = AsyncMock()
    mock_client.audio.speech.create = AsyncMock(return_value=mock_response)

    long_text = "x" * 5000
    with patch("app.tts.openai.AsyncOpenAI", return_value=mock_client):
        await synthesize(long_text)

    call_kwargs = mock_client.audio.speech.create.call_args.kwargs
    assert len(call_kwargs["input"]) <= 4096


# ── MTD routing helper tests ──────────────────────────────────────────────────

from app.main import _is_mtd_question


def test_is_mtd_question_true():
    assert _is_mtd_question("When is my HMRC deadline?") is True
    assert _is_mtd_question("What is MTD for self assessment?") is True
    assert _is_mtd_question("Submit my quarterly report") is True


def test_is_mtd_question_false():
    assert _is_mtd_question("What is my bank balance?") is False
    assert _is_mtd_question("Show me my invoices") is False


# ── FastAPI REST smoke tests ──────────────────────────────────────────────────

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app as fastapi_app
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "voice-gateway"


def test_voice_text_agent_error(client):
    """voice/text should return a response even when agent is unreachable."""
    r = client.post("/voice/text", json={"user_id": "u1", "text": "What is my balance?"})
    assert r.status_code == 200
    assert "response" in r.json() or "error" in r.json()


def test_voice_speak_no_key(client):
    """voice/speak without API key returns error dict, not 500."""
    import app.tts as tts_module
    original = tts_module.OPENAI_API_KEY
    tts_module.OPENAI_API_KEY = ""
    r = client.post("/voice/speak", json={"user_id": "u1", "text": "Hello"})
    assert r.status_code == 200
    assert "error" in r.json()
    tts_module.OPENAI_API_KEY = original
