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

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .agent import generate_response
from .models import (
    Base,
    ChatSessionORM,
    ChatStats,
    FeedbackCreate,
    FeedbackORM,
    TicketCreate,
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

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="SelfMonitor Support AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory session history (production: use Redis) ─────────────────────────
_session_history: dict[str, list[dict]] = {}


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
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    ticket = TicketORM(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info("Ticket created: %s by %s", ticket.id, ticket.user_email)
    return ticket


@app.get("/tickets", response_model=List[TicketOut])
def list_tickets(
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
def update_ticket_status(
    ticket_id: str,
    status: str = Query(..., regex="^(open|in_progress|resolved|closed)$"),
    db: Session = Depends(get_db),
):
    ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.status = status
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": ticket_id, "status": status}


# ── Feedback endpoint ──────────────────────────────────────────────────────────
@app.post("/feedback", status_code=201)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)):
    fb = FeedbackORM(**payload.model_dump())
    db.add(fb)
    db.commit()
    return {"ok": True, "id": fb.id}


# ── Stats (admin) ──────────────────────────────────────────────────────────────
@app.get("/stats", response_model=ChatStats)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(TicketORM).count()
    open_ = db.query(TicketORM).filter(TicketORM.status == "open").count()
    resolved = db.query(TicketORM).filter(TicketORM.status == "resolved").count()
    sessions = db.query(ChatSessionORM).count()

    feedbacks = db.query(FeedbackORM).all()
    avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks) if feedbacks else 0.0

    return ChatStats(
        total_tickets=total,
        open_tickets=open_,
        resolved_tickets=resolved,
        avg_rating=round(avg_rating, 1),
        total_sessions=sessions,
    )


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "support-ai-service", "version": "1.0.0"}
