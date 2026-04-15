"""
support-ai-service — FastAPI application
Port: 8020

Endpoints:
  WebSocket  /ws/chat/{session_id}   — real-time AI chat
  POST       /tickets                — create support ticket
  GET        /tickets                — list tickets (admin)
  PATCH      /tickets/{id}/status    — update ticket status
  POST       /feedback               — submit star rating
  GET        /stats                  — aggregate stats (admin)
  GET        /health                 — health check
"""

import asyncio
import json as _json
import logging
import os
from datetime import datetime, timezone
from typing import Any, List, Optional, cast

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.orm import Session

from .agent import generate_response
from .models import (
    Base,
    ChatSessionORM,
    ChatStats,
    FeedbackCreate,
    FeedbackORM,
    TicketAssignBody,
    TicketCreate,
    TicketMessageCreate,
    TicketMessageORM,
    TicketMessageOut,
    TicketORM,
    TicketOut,
    engine,
    get_db,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("support-ai-service")

# ── DB init ───────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE tickets ADD COLUMN assigned_to VARCHAR"))
    except Exception:
        pass

AUTH_SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "").strip()


def _decode_support_jwt(authorization: str | None) -> dict[str, Any]:
    if not AUTH_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTH_SECRET_KEY is not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = authorization[7:].strip()
    try:
        return jwt.decode(token, AUTH_SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc


def _jwt_allows_support_operator(payload: dict[str, Any]) -> bool:
    if payload.get("is_admin"):
        return True
    perms = payload.get("perms")
    if isinstance(perms, list) and "*" in {str(p) for p in perms}:
        return True
    scopes = payload.get("scopes")
    if not isinstance(scopes, list):
        return False
    s = {str(x) for x in scopes}
    return "support:*" in s or "support:read" in s or "support:write" in s


def require_support_admin(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = _decode_support_jwt(authorization)
    if not _jwt_allows_support_operator(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return payload

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="SelfMonitor Support AI Service", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory session history (production: use Redis) ─────────────────────────
_session_history: dict[str, list[dict[str, Any]]] = {}

# ── ADM.10: Notification hub ────────────────────────────────────────────────────
_admin_ws_clients: set[WebSocket] = set()


async def _broadcast_notification(event_type: str, data: dict) -> None:
    """Push an event to all connected admin WS clients (fire-and-forget)."""
    if not _admin_ws_clients:
        return
    message = _json.dumps({"type": event_type, **data})
    dead: set[WebSocket] = set()
    for ws in list(_admin_ws_clients):
        try:
            await ws.send_text(message)
        except Exception:  # noqa: BLE001
            dead.add(ws)
    _admin_ws_clients.difference_update(dead)


# ── WebSocket chat ─────────────────────────────────────────────────────────────
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info("WS connected: %s", session_id)

    history = _session_history.setdefault(session_id, [])
    user_email: Optional[str] = None

    # -- Greet immediately --
    greeting, _ = generate_response("hello", [], user_email)
    await websocket.send_json(
        {"role": "assistant", "content": greeting, "session_id": session_id}
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_text: str = data.get("content", "").strip()
            user_email = data.get("user_email") or user_email

            if not msg_text:
                continue

            history.append({"role": "user", "content": msg_text})

            # Generate response
            response_text, intent = generate_response(msg_text, history, user_email)

            history.append({"role": "assistant", "content": response_text})

            # Keep history bounded
            if len(history) > 40:
                history = history[-40:]
                _session_history[session_id] = history

            await websocket.send_json(
                {
                    "role": "assistant",
                    "content": response_text,
                    "intent": intent,
                    "session_id": session_id,
                }
            )

    except WebSocketDisconnect:
        logger.info("WS disconnected: %s", session_id)
        _session_history.pop(session_id, None)


# ── Ticket endpoints ───────────────────────────────────────────────────────────
@app.post("/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    ticket = TicketORM(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info("Ticket created: %s by %s", ticket.id, ticket.user_email)
    asyncio.create_task(
        _broadcast_notification(
            "ticket.created",
            {
                "ticket_id": str(ticket.id),
                "user_email": ticket.user_email,
                "subject": ticket.subject,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            },
        )
    )
    return ticket


@app.get("/tickets", response_model=List[TicketOut])
def list_tickets(
    _admin: dict = Depends(require_support_admin),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(TicketORM)
    if status:
        q = q.filter(TicketORM.status == status)
    if priority:
        q = q.filter(TicketORM.priority == priority)
    return q.order_by(TicketORM.created_at.desc()).limit(limit).all()


@app.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    _admin: dict = Depends(require_support_admin),
    ticket_status: str = Query(
        ...,
        alias="status",
        pattern="^(open|in_progress|resolved|closed)$",
    ),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    setattr(ticket, "status", ticket_status)
    setattr(ticket, "updated_at", datetime.now(timezone.utc))
    db.commit()
    asyncio.create_task(
        _broadcast_notification(
            "ticket.status_changed",
            {"ticket_id": ticket_id, "new_status": ticket_status},
        )
    )
    return {"id": ticket_id, "status": ticket_status}


# ── Feedback endpoint ──────────────────────────────────────────────────────────
@app.post("/feedback", status_code=201)
def submit_feedback(
    payload: FeedbackCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    fb = FeedbackORM(**payload.model_dump())
    db.add(fb)
    db.commit()
    return {"ok": True, "id": str(fb.id)}


# ── Stats (admin) ──────────────────────────────────────────────────────────────
@app.get("/stats", response_model=ChatStats)
def get_stats(
    _admin: dict = Depends(require_support_admin),
    db: Session = Depends(get_db),
):
    total = db.query(TicketORM).count()
    open_ = db.query(TicketORM).filter(TicketORM.status == "open").count()
    resolved = db.query(TicketORM).filter(TicketORM.status == "resolved").count()
    sessions = db.query(ChatSessionORM).count()

    feedbacks = db.query(FeedbackORM).all()
    avg_rating: float = (
        sum(cast(int, f.rating) for f in feedbacks) / len(feedbacks)
        if feedbacks
        else 0.0
    )

    return ChatStats(
        total_tickets=total,
        open_tickets=open_,
        resolved_tickets=resolved,
        avg_rating=round(float(avg_rating), 1),
        total_sessions=sessions,
    )


@app.get("/tickets/{ticket_id}/messages", response_model=List[TicketMessageOut])
def list_ticket_messages(
    ticket_id: str,
    _admin: dict = Depends(require_support_admin),
    db: Session = Depends(get_db),
):
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    rows = (
        db.query(TicketMessageORM)
        .filter(TicketMessageORM.ticket_id == ticket_id)
        .order_by(TicketMessageORM.created_at.asc())
        .all()
    )
    return rows


@app.post("/tickets/{ticket_id}/messages", response_model=TicketMessageOut, status_code=201)
def add_ticket_message(
    ticket_id: str,
    payload: TicketMessageCreate,
    _admin: dict = Depends(require_support_admin),
    db: Session = Depends(get_db),
):
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    msg = TicketMessageORM(
        ticket_id=ticket_id,
        author_role=payload.author_role,
        body=payload.body,
    )
    db.add(msg)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


@app.patch("/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: str,
    body: TicketAssignBody,
    _admin: dict = Depends(require_support_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.assigned_to = body.assigned_to
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": ticket_id, "assigned_to": body.assigned_to}


@app.patch("/tickets/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: str,
    _admin: dict = Depends(require_support_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.status = "resolved"
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": ticket_id, "status": "resolved"}


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "support-ai-service", "version": "1.0.0"}


# ── ADM.10: Admin notification WebSocket ───────────────────────────────────────
@app.websocket("/ws/admin/notifications")
async def ws_admin_notifications(websocket: WebSocket):
    """
    Real-time admin notification stream.
    Client must send a valid admin Bearer token as the first text message
    within 5 seconds after connecting, otherwise the connection is closed.
    Events pushed: ticket.created, ticket.status_changed, stats.updated
    """
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await websocket.close(code=1008, reason="Auth timeout")
        return

    token = raw.strip()
    if token.startswith("Bearer "):
        token = token[7:]
    try:
        payload = _decode_support_jwt(f"Bearer {token}")
        if not _jwt_allows_support_operator(payload):
            raise ValueError("Insufficient permissions")
    except Exception:  # noqa: BLE001
        await websocket.close(code=1008, reason="Unauthorized")
        return

    _admin_ws_clients.add(websocket)
    logger.info("Admin WS connected — %d clients", len(_admin_ws_clients))
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text(_json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        _admin_ws_clients.discard(websocket)
        logger.info("Admin WS disconnected — %d clients", len(_admin_ws_clients))
