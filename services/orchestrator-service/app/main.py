"""
Orchestrator Service — Master AI Agent entry point.

POST /orchestrate          → route user message through multi-agent system
GET  /agents/status        → which agents are active, kill-switch state
POST /agents/{name}/disable→ kill-switch for a specific agent
POST /agents/{name}/enable → re-enable an agent
GET  /audit/{user_id}      → agent action log for compliance
GET  /health
"""
from __future__ import annotations

import datetime
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from fastapi.responses import Response

from .orchestrator import MasterOrchestrator, _DISABLED_AGENTS
from .memory.shared_context import append_audit_log, get_audit_log, set_user_context

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM  = "HS256"

app = FastAPI(
    title="Orchestrator Service",
    description="Master AI Orchestrator: decomposes requests → specialist agents → aggregated response.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

ORCHESTRATE_REQUESTS = Counter(
    "orchestrator_requests_total", "Total orchestration requests", ["status"]
)
ORCHESTRATE_LATENCY = Histogram(
    "orchestrator_latency_seconds", "Orchestration latency",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
)

_orchestrator = MasterOrchestrator()


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError:
        raise exc
    user_id = payload.get("sub")
    if not user_id:
        raise exc
    return str(user_id)


# ── Request / Response models ──────────────────────────────────────────────────

class OrchestrateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=3000)
    session_id: Optional[str] = None
    language: str = Field(default="en")
    context: Optional[Dict[str, Any]] = None


class AgentResultOut(BaseModel):
    agent: str
    success: bool
    summary: str
    confidence: float
    actions_taken: List[str]
    warnings: List[str]
    elapsed_ms: int


class OrchestrateResponse(BaseModel):
    response: str
    session_id: str
    agents_used: List[str]
    confidence: float
    actions_taken: List[str]
    warnings: List[str]
    agent_results: List[AgentResultOut]
    processing_time_ms: int
    generated_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "orchestrator-service",
        "agents": _orchestrator.agent_status(),
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(
    req: OrchestrateRequest,
    user_id: str = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
) -> OrchestrateResponse:
    """Route user message through the multi-agent system."""
    session_id = req.session_id or f"sess_{user_id}_{uuid.uuid4().hex[:8]}"

    ORCHESTRATE_REQUESTS.labels(status="started").inc()

    with ORCHESTRATE_LATENCY.time():
        result = await _orchestrator.handle(
            user_message=req.message,
            token=token,
            session_id=session_id,
        )

    ORCHESTRATE_REQUESTS.labels(status="success").inc()

    # Persist audit log (non-blocking)
    import asyncio
    asyncio.create_task(append_audit_log(user_id, {
        "ts": datetime.datetime.now(datetime.UTC).isoformat(),
        "session_id": session_id,
        "message": req.message[:200],
        "agents": result.agents_used,
        "confidence": result.confidence,
        "warnings": result.warnings,
        "processing_ms": result.processing_time_ms,
    }))

    # Update shared context with latest agent data
    finance_result = next((r for r in result.agent_results if r.agent == "finance"), None)
    if finance_result and finance_result.success:
        asyncio.create_task(set_user_context(user_id, {
            "last_summary": finance_result.data.get("summary"),
            "last_orchestration": datetime.datetime.now(datetime.UTC).isoformat(),
        }))

    return OrchestrateResponse(
        response=result.response,
        session_id=session_id,
        agents_used=result.agents_used,
        confidence=result.confidence,
        actions_taken=result.actions_taken,
        warnings=result.warnings,
        agent_results=[
            AgentResultOut(
                agent=r.agent,
                success=r.success,
                summary=r.summary,
                confidence=r.confidence,
                actions_taken=r.actions_taken,
                warnings=r.warnings,
                elapsed_ms=r.elapsed_ms,
            )
            for r in result.agent_results
        ],
        processing_time_ms=result.processing_time_ms,
        generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
    )


@app.get("/agents/status")
async def agents_status(_user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Which agents are active. Admin can see kill-switch state."""
    return {
        "agents": _orchestrator.agent_status(),
        "disabled": list(_DISABLED_AGENTS),
    }


@app.post("/agents/{agent_name}/disable")
async def disable_agent(
    agent_name: str,
    _user_id: str = Depends(get_current_user),
) -> Dict[str, str]:
    """Kill-switch: immediately disable a specific agent."""
    valid = {"tax", "finance", "document", "support"}
    if agent_name not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown agent. Valid: {valid}")
    _DISABLED_AGENTS.add(agent_name)
    log.warning("Agent '%s' disabled by user %s", agent_name, _user_id)
    return {"status": "disabled", "agent": agent_name}


@app.post("/agents/{agent_name}/enable")
async def enable_agent(
    agent_name: str,
    _user_id: str = Depends(get_current_user),
) -> Dict[str, str]:
    """Re-enable a previously disabled agent."""
    _DISABLED_AGENTS.discard(agent_name)
    return {"status": "enabled", "agent": agent_name}


@app.get("/audit/{user_id}")
async def get_audit(
    user_id: str,
    limit: int = 20,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compliance audit trail — users can only access their own log."""
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Access denied")
    log_entries = await get_audit_log(user_id, limit=limit)
    return {"user_id": user_id, "entries": log_entries, "count": len(log_entries)}
