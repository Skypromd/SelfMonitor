"""Structured audit-friendly logging when a request is denied due to plan limits."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_log = logging.getLogger("plan_enforcement")


def _sync_compliance_audit(user_id: str, details: dict[str, Any], bearer_token: str) -> None:
    if os.getenv("PLAN_ENFORCEMENT_COMPLIANCE_SYNC", "1").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        return
    base = os.getenv("COMPLIANCE_SERVICE_URL", "").strip().rstrip("/")
    if not base:
        return
    try:
        import httpx

        httpx.post(
            f"{base}/audit-events",
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            },
            json={
                "user_id": user_id,
                "action": "plan_enforcement_denied",
                "details": details,
            },
            timeout=3.0,
        )
    except Exception:
        pass


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
    compliance_bearer_token: str | None = None,
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
    if compliance_bearer_token:
        _sync_compliance_audit(user_id, payload, compliance_bearer_token)
