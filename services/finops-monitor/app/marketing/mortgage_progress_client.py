"""Shared analytics call for Road to mortgage (finops scheduled jobs)."""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any

import httpx
from jose import jwt as jose_jwt

log = logging.getLogger(__name__)


def mint_worker_bearer(user_email: str) -> str:
    now = datetime.datetime.now(datetime.UTC)
    exp = now + datetime.timedelta(minutes=12)
    secret = os.environ["AUTH_SECRET_KEY"].strip()
    payload: dict[str, Any] = {
        "sub": user_email.strip().lower(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


async def fetch_mortgage_progress_payload(user_email: str) -> dict[str, Any] | None:
    base = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:80").rstrip("/")
    token = mint_worker_bearer(user_email)
    body = {"credit_focus": "unknown", "include_backend_signals": True}
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{base}/mortgage/progress-tracker",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
    except httpx.HTTPError as exc:
        log.warning("mortgage progress HTTP error for %s: %s", user_email, exc)
        return None
    if resp.status_code >= 400:
        log.warning(
            "mortgage progress %s for %s: %s",
            resp.status_code,
            user_email,
            (resp.text or "")[:300],
        )
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def parse_current_step_id_and_title(data: dict[str, Any]) -> tuple[str | None, str | None]:
    step_id = data.get("current_step_id")
    if not isinstance(step_id, str) or not step_id.strip():
        return None, None
    sid = step_id.strip()
    title: str | None = None
    steps = data.get("steps")
    if isinstance(steps, list):
        for row in steps:
            if not isinstance(row, dict):
                continue
            if row.get("id") == sid and row.get("status") == "current":
                t = row.get("title")
                if isinstance(t, str) and t.strip():
                    title = t.strip()
                break
    return sid, title
