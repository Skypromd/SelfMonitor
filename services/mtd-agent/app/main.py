"""
MTD Agent Service — FastAPI on port 8022

Endpoints:
  GET  /health
  GET  /status/{user_id}          – current quarter + GPT-4 explanation
  POST /question/{user_id}        – answer free-form MTD question
  POST /submit/{user_id}          – direct HMRC test-api period summary (OAuth token)
  GET  /hmrc/callback             – HMRC OAuth2 callback handler

Production MTD filing with draft/confirm and transactions-backed figures should use
**tax-engine** + **integrations-service** (see AGENTS.md). This service keeps direct
submit for sandbox demos; period JSON is built via **libs.shared_mtd** to match
that shape.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.hmrc_client import HMRCClient
from app.hmrc_token_store import get_hmrc_user_access_token, store_hmrc_user_access_token
from app.mtd_agent import MTDAgent
from app.redis_client import create_redis_client

for _parent in Path(__file__).resolve().parents:
    if (_parent / "libs").exists():
        _rp = str(_parent)
        if _rp not in sys.path:
            sys.path.append(_rp)
        break
from libs.shared_http.request_id import RequestIdMiddleware

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]

redis_client: object = None
mtd_agent: MTDAgent  = None  # type: ignore
hmrc_client          = HMRCClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, mtd_agent
    redis_client = await create_redis_client()
    mtd_agent    = MTDAgent(redis_client)
    log.info("MTD Agent service started on port 8022")
    yield
    if redis_client:
        await redis_client.aclose()  # type: ignore


app = FastAPI(
    title="MTD Agent",
    description="HMRC MTD ITSA compliance advisor with GPT-4 explanations",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mtd-agent"}


@app.get("/status/{user_id}")
async def mtd_status(user_id: str, language: str = "en"):
    """Return current quarter MTD status with AI explanation."""
    result = await mtd_agent.get_mtd_status(user_id, language=language)
    return result.to_dict()


class QuestionPayload(BaseModel):
    question: str
    language: str = "en"


@app.post("/question/{user_id}")
async def ask_question(user_id: str, payload: QuestionPayload):
    """Answer a free-form MTD / tax question with user context."""
    answer = await mtd_agent.answer_question(user_id, payload.question, language=payload.language)
    return {
        "user_id":  user_id,
        "question": payload.question,
        "answer":   answer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class SubmitPayload(BaseModel):
    nino: str                           # National Insurance number
    tax_year: str                       # e.g. "2026-27"
    period_start: str                   # ISO date "2026-04-06"
    period_end: str                     # ISO date "2026-07-05"
    income: float
    expenses: float
    hmrc_access_token: str | None = None  # if None, uses stored token


@app.post("/submit/{user_id}")
async def submit_to_hmrc(user_id: str, payload: SubmitPayload):
    """Trigger MTD quarterly submission to HMRC."""
    token = payload.hmrc_access_token
    if not token and redis_client:
        token = await get_hmrc_user_access_token(redis_client, user_id)
    if not token:
        raise HTTPException(
            401,
            "No HMRC access token. Complete OAuth flow at /hmrc/callback first.",
        )
    try:
        receipt = await hmrc_client.submit_period_summary(
            nino=payload.nino,
            tax_year=payload.tax_year,
            period_start=payload.period_start,
            period_end=payload.period_end,
            income=payload.income,
            expenses=payload.expenses,
            access_token=token,
        )
        return {
            "status":    "submitted",
            "receipt":   receipt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        log.error("HMRC submission failed for user %s: %s", user_id, exc)
        raise HTTPException(502, f"HMRC submission failed: {exc}") from exc


@app.get("/hmrc/callback")
async def hmrc_oauth_callback(code: str, state: str | None = None):
    """
    HMRC OAuth2 redirect callback.
    After user authorises on HMRC website, they are redirected here with ?code=...
    state should contain the user_id (set during the initial auth redirect).
    """
    if not state:
        raise HTTPException(400, "Missing state parameter (user_id)")
    try:
        token, expires_in = await hmrc_client.exchange_authorization_code(code)
        if redis_client:
            await store_hmrc_user_access_token(redis_client, state, token, expires_in)
        return {
            "status":  "authorised",
            "user_id": state,
            "message": "HMRC access token stored. You can now submit MTD returns.",
        }
    except Exception as exc:
        raise HTTPException(502, f"HMRC OAuth failed: {exc}") from exc
