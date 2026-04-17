"""Daily bank sync quota per user (UTC calendar day). See BANK_SYNC_ECONOMICS.md."""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status

for _parent in Path(__file__).resolve().parents:
    if (_parent / "libs").exists():
        _root = str(_parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        break

from libs.shared_auth.plan_enforcement_log import log_plan_enforcement_denial
from libs.shared_http.request_id import get_request_id

_LOCK = threading.Lock()


def _store_path() -> Path:
    return Path(os.getenv("BANKING_SYNC_USAGE_PATH", "/data/bank_sync_usage.json"))


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load() -> dict[str, dict[str, int]]:
    p = _store_path()
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        out: dict[str, dict[str, int]] = {}
        for uid, days in raw.items():
            if not isinstance(days, dict):
                continue
            inner: dict[str, int] = {}
            for dkey, count in days.items():
                try:
                    inner[str(dkey)] = int(count)
                except (TypeError, ValueError):
                    continue
            out[str(uid)] = inner
        return out
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}


def _save(data: dict[str, dict[str, int]]) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def sync_used_today(user_id: str) -> int:
    with _LOCK:
        data = _load()
        return int(data.get(user_id, {}).get(_today_utc(), 0))


def consume_sync_slot_or_raise(
    user_id: str, daily_limit: int, *, plan: str = "unknown"
) -> None:
    """Atomically consume one manual sync for today (UTC) or raise 403."""
    if daily_limit <= 0:
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=plan,
            feature="bank_sync_daily",
            reason="sync_not_in_plan",
            current=0,
            limit_value=0,
            request_id=get_request_id(),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank sync is not included in your plan. Upgrade to use manual sync.",
        )
    day = _today_utc()
    with _LOCK:
        data = _load()
        if user_id not in data:
            data[user_id] = {}
        used = int(data[user_id].get(day, 0))
        if used >= daily_limit:
            log_plan_enforcement_denial(
                user_id=user_id,
                plan=plan,
                feature="bank_sync_daily",
                reason="daily_cap_exceeded",
                current=used,
                limit_value=daily_limit,
                request_id=get_request_id(),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Daily bank sync limit reached ({daily_limit} per day, UTC). "
                    "Try again tomorrow or upgrade your plan."
                ),
            )
        data[user_id][day] = used + 1
        _save(data)


def sync_status(user_id: str, daily_limit: int) -> dict[str, int]:
    used = sync_used_today(user_id)
    remaining = max(0, daily_limit - used) if daily_limit > 0 else 0
    return {"daily_limit": daily_limit, "used_today": used, "remaining": remaining}
