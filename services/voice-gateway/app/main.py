"""
Voice Gateway — FastAPI on port 8023

WebSocket protocol
------------------
Client → Server:
  { "type": "audio", "user_id": "...", "data": "<base64 webm>", "lang": "en" }
  { "type": "text",  "user_id": "...", "text": "What is my balance?" }

Server → Client:
  { "type": "transcript", "text": "..." }          — STT result
  { "type": "response",   "text": "...", "audio": "<base64 mp3>" }
  { "type": "error",      "message": "..." }

REST endpoints:
  GET  /health
  POST /voice/text   – text only (returns JSON with AI response, no audio)
  POST /voice/speak  – text → MP3 audio bytes
"""

from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.stt import transcribe
from app.tts import synthesize

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

AUTH_SECRET_KEY     = os.environ["AUTH_SECRET_KEY"]
AGENT_SERVICE_URL   = os.getenv("AGENT_SERVICE_URL",  "http://ai-agent-service:80")
MTD_AGENT_URL       = os.getenv("MTD_AGENT_URL",       "http://mtd-agent:8022")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Voice Gateway started on port 8023")
    yield


app = FastAPI(
    title="Voice Gateway",
    description="WebSocket voice interface: Whisper STT → SelfMate → OpenAI TTS",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

async def _ask_agent(user_id: str, text: str, language: str = "en") -> str:
    """Forward text to SelfMate AI agent and return its response."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{AGENT_SERVICE_URL}/chat",
            json={"user_id": user_id, "message": text, "language": language},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response") or data.get("message") or str(data)


async def _ask_mtd_agent(user_id: str, text: str, language: str = "en") -> str:
    """Forward MTD-related questions to the MTD Agent."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{MTD_AGENT_URL}/question/{user_id}",
            json={"question": text, "language": language},
        )
        resp.raise_for_status()
        return resp.json().get("answer", "")


_MTD_KEYWORDS = {"mtd", "hmrc", "tax return", "quarterly report", "self assessment", "itsa"}


def _is_mtd_question(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _MTD_KEYWORDS)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket):
    """
    Bidirectional voice chat WebSocket.

    Accepts audio (base64 webm) or text messages.
    Responds with AI reply + synthesised MP3 audio (base64).
    """
    await websocket.accept()
    log.info("Voice WebSocket connection opened")

    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")
            user_id  = msg.get("user_id", "anonymous")

            if msg_type == "audio":
                # Step 1: STT
                try:
                    audio_b64 = msg["data"]
                    audio_bytes = base64.b64decode(audio_b64)
                    lang = msg.get("lang", "en")
                    transcript = await transcribe(audio_bytes, language=lang)
                except Exception as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue

                await websocket.send_json({"type": "transcript", "text": transcript})
                text = transcript

            elif msg_type == "text":
                text = msg.get("text", "")
                lang = msg.get("lang", "en")
                if not text:
                    await websocket.send_json({"type": "error", "message": "Empty text"})
                    continue
            else:
                await websocket.send_json({"type": "error", "message": f"Unknown type: {msg_type}"})
                continue

            # Step 2: Route to agent
            try:
                if _is_mtd_question(text):
                    response_text = await _ask_mtd_agent(user_id, text, language=lang)
                else:
                    response_text = await _ask_agent(user_id, text, language=lang)
            except Exception as exc:
                log.error("Agent error: %s", exc)
                response_text = "I'm having trouble connecting to the AI service right now. Please try again."

            # Step 3: TTS
            try:
                audio_out = await synthesize(response_text)
                audio_out_b64 = base64.b64encode(audio_out).decode()
            except Exception as exc:
                log.warning("TTS failed, sending text only: %s", exc)
                audio_out_b64 = ""

            await websocket.send_json({
                "type":  "response",
                "text":  response_text,
                "audio": audio_out_b64,
            })

    except WebSocketDisconnect:
        log.info("Voice WebSocket connection closed")
    except Exception as exc:
        log.error("Voice WebSocket error: %s", exc, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": "Internal error"})
        except Exception:
            pass


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "voice-gateway"}


class TextRequest(BaseModel):
    user_id: str
    text: str


@app.post("/voice/text")
async def voice_text(req: TextRequest):
    """Text-in → AI response text-out (no audio generation)."""
    try:
        if _is_mtd_question(req.text):
            response = await _ask_mtd_agent(req.user_id, req.text)
        else:
            response = await _ask_agent(req.user_id, req.text)
    except Exception as exc:
        response = f"Agent unavailable: {exc}"
    return {"user_id": req.user_id, "input": req.text, "response": response}


@app.post("/voice/speak")
async def voice_speak(req: TextRequest):
    """Text-in → MP3 audio bytes (base64 encoded)."""
    try:
        audio = await synthesize(req.text)
        return {
            "user_id": req.user_id,
            "audio_b64": base64.b64encode(audio).decode(),
            "format":   "mp3",
        }
    except Exception as exc:
        return {"error": str(exc)}
