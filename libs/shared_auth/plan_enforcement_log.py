"""Structured audit-friendly logging when a request is denied due to plan limits."""

from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger("plan_enforcement")


def log_plan_enforcement_denial(
    *,
    user_id: str,
    plan: str,
    feature: str,
    reason: str,
    current: int | float | None = None,
    limit_value: int | float | None = None,
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "plan_enforcement_event",
        "user_id": user_id,
        "plan": plan,
        "feature": feature,
        "reason": reason,
    }
    if current is not None:
        payload["current"] = current
    if limit_value is not None:
        payload["limit"] = limit_value
    if request_id:
        payload["request_id"] = request_id
    if extra:
        payload["extra"] = extra
    _log.info("%s", json.dumps(payload, default=str))
