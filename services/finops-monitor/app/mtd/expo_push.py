"""Expo Push API client for MTD deadline notifications (mobile)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def validate_expo_push_token_format(value: str) -> bool:
    v = (value or "").strip()
    return v.startswith("ExponentPushToken[") or v.startswith("ExpoPushToken[")


async def send_expo_push_notification(
    *,
    to_token: str,
    title: str,
    body: str,
) -> None:
    payload: dict[str, Any] = {
        "to": to_token,
        "title": title[:200],
        "body": body[:300],
        "sound": "default",
        "priority": "high",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            EXPO_PUSH_URL,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("expo_push_invalid_response")
    if data.get("errors"):
        raise RuntimeError(str(data["errors"]))
    items = data.get("data")
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict) and first.get("status") == "error":
            raise RuntimeError(str(first.get("message", first)))
