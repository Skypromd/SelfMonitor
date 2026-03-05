"""Database models and Pydantic schemas for the support-ai-service."""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Database setup ─────────────────────────────────────────────────────────────
DB_PATH = os.getenv("SUPPORT_DB_PATH", "support.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── ORM models ─────────────────────────────────────────────────────────────────
class TicketORM(Base):
    __tablename__ = "tickets"

    id = Column(
        String, primary_key=True, default=lambda: f"SM-{uuid.uuid4().hex[:5].upper()}"
    )
    user_email = Column(String, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class FeedbackORM(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String, nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatSessionORM(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    user_email = Column(String, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    message_count = Column(Integer, default=0)
    resolved = Column(Integer, default=0)  # 0=open, 1=resolved, 2=escalated


# ── Pydantic I/O schemas ───────────────────────────────────────────────────────
class TicketCreate(BaseModel):
    user_email: str
    category: str
    priority: str = "medium"
    subject: str
    message: str

    @field_validator("priority")
    @classmethod
    def check_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v

    @field_validator("category")
    @classmethod
    def check_category(cls, v: str) -> str:
        allowed = {"billing", "technical", "account", "feature", "other"}
        if v not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v


class TicketOut(BaseModel):
    id: str
    user_email: str
    category: str
    priority: str
    subject: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    user_email: Optional[str] = None
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("rating must be 1-5")
        return v


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatStats(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    avg_rating: float
    total_sessions: int
