"""Failed-login lockout backed by SQLite (survives process restarts)."""

from __future__ import annotations

import datetime

from fastapi import HTTPException, status

from app.config import (
    LOCKOUT_THRESHOLD,
    LOCKOUT_WINDOW_MINUTES,
    LOCKOUT_WINDOW_SECONDS,
)
from app.db import _connect, db_lock


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def check_account_lockout(email: str) -> None:
    if count_recent_failed_attempts(email) >= LOCKOUT_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Account temporarily locked. Try again in "
                f"{LOCKOUT_WINDOW_MINUTES} minute(s)."
            ),
        )


def record_failed_attempt(email: str) -> None:
    key = _normalize_email(email)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO login_failed_attempts (email, attempted_at) VALUES (?, ?)",
                (key, now),
            )
            conn.commit()
        finally:
            conn.close()


def clear_failed_attempts(email: str) -> None:
    key = _normalize_email(email)
    with db_lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM login_failed_attempts WHERE email = ?", (key,))
            conn.commit()
        finally:
            conn.close()


def count_recent_failed_attempts(email: str) -> int:
    key = _normalize_email(email)
    cutoff = (
        datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(seconds=LOCKOUT_WINDOW_SECONDS)
    ).isoformat()
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM login_failed_attempts WHERE email = ? AND attempted_at > ?",
                (key, cutoff),
            ).fetchone()
        finally:
            conn.close()
    return int(row["c"]) if row else 0


def prune_old_login_attempts() -> None:
    """Optional housekeeping; called from init."""
    cutoff = (
        datetime.datetime.now(datetime.UTC)
        - datetime.timedelta(seconds=LOCKOUT_WINDOW_SECONDS * 4)
    ).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "DELETE FROM login_failed_attempts WHERE attempted_at < ?", (cutoff,)
            )
            conn.commit()
        finally:
            conn.close()
