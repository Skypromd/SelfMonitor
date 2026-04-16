"""SQLite connection for auth-service."""

from __future__ import annotations

import sqlite3
import threading

from app.config import AUTH_DB_PATH

db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
