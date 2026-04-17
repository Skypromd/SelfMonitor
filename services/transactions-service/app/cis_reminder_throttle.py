"""CIS reminder anti-spam: hard 72h; soft cap 2 per 7d then in-app only until window clears."""
from __future__ import annotations

import datetime
from typing import Any

HARD_INTERVAL_HOURS = 72
SOFT_MAX_IN_7D = 2
SOFT_WINDOW_DAYS = 7


def _parse_ts(raw: str | None) -> datetime.datetime | None:
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def reminder_send_allowed(reminder_meta: dict[str, Any] | None, now: datetime.datetime) -> tuple[bool, str]:
    """
    Returns (allowed, reason_code).
    reason_code: ok | hard_throttle | soft_throttle
    """
    now_u = now.replace(tzinfo=datetime.UTC) if now.tzinfo is None else now.astimezone(datetime.UTC)
    meta = reminder_meta or {}
    history: list[str] = list(meta.get("sent_history") or [])
    if not history:
        return True, "ok"

    last = _parse_ts(history[-1])
    if last:
        last_u = last.replace(tzinfo=datetime.UTC) if last.tzinfo is None else last.astimezone(datetime.UTC)
        if now_u - last_u < datetime.timedelta(hours=HARD_INTERVAL_HOURS):
            return False, "hard_throttle"

    cutoff = now_u - datetime.timedelta(days=SOFT_WINDOW_DAYS)
    recent = 0
    for h in history:
        ts = _parse_ts(h)
        if not ts:
            continue
        ts_utc = ts.replace(tzinfo=datetime.UTC) if ts.tzinfo is None else ts.astimezone(datetime.UTC)
        if ts_utc >= cutoff:
            recent += 1
    if recent >= SOFT_MAX_IN_7D:
        return False, "soft_throttle"

    return True, "ok"


def append_sent_timestamp(meta: dict[str, Any] | None, now: datetime.datetime) -> dict[str, Any]:
    out = dict(meta or {})
    hist = list(out.get("sent_history") or [])
    now_u = now.replace(tzinfo=datetime.UTC) if now.tzinfo is None else now.astimezone(datetime.UTC)
    hist.append(now_u.isoformat().replace("+00:00", "Z"))
    out["sent_history"] = hist[-20:]
    return out
