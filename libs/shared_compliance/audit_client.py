"""Forward audit events to compliance-service using the end-user JWT (same sub as user_id)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def post_audit_event(
    *,
    compliance_base_url: str,
    bearer_token: str,
    user_id: str,
    action: str,
    details: dict[str, Any] | None = None,
    timeout_seconds: float = 8.0,
) -> bool:
    base = compliance_base_url.strip().rstrip("/")
    if not base:
        return False
    url = f"{base}/audit-events"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                json={"user_id": user_id, "action": action, "details": details or {}},
            )
        if resp.status_code >= 400:
            logger.warning("compliance audit POST %s: %s %s", action, resp.status_code, resp.text[:500])
            return False
        return True
    except Exception as exc:
        logger.warning("compliance audit POST failed action=%s: %s", action, exc)
        return False
