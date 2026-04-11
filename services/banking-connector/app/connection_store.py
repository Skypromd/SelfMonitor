"""Persistent-ish count of completed Open Banking connections per user (email / JWT sub)."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

_LOCK = threading.Lock()


def _store_path() -> Path:
    return Path(
        os.getenv("BANKING_CONNECTIONS_STORE_PATH", "/tmp/banking_user_connections.json")
    )


def _load() -> dict[str, int]:
    _STORE_PATH = _store_path()
    if not _STORE_PATH.exists():
        return {}
    try:
        raw = _STORE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return {str(k): int(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}


def _save(data: dict[str, int]) -> None:
    _STORE_PATH = _store_path()
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    tmp.replace(_STORE_PATH)


def get_connection_count(user_id: str) -> int:
    with _LOCK:
        return _load().get(user_id, 0)


def increment_connection_count(user_id: str) -> int:
    with _LOCK:
        data = _load()
        n = int(data.get(user_id, 0)) + 1
        data[user_id] = n
        _save(data)
        return n
