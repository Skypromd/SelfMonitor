"""
Balance monitor — fetches account balances from the transactions service
and publishes a low-balance warning when below the configured threshold.

transactions-service: internal port 8003 (or $TRANSACTIONS_SERVICE_URL).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from app.redis_bus import publish_event, EventType

log = logging.getLogger(__name__)

TRANSACTIONS_SERVICE_URL = os.getenv(
    "TRANSACTIONS_SERVICE_URL", "http://transactions-service:8003"
)

# Alert when available balance drops below this value (£)
LOW_BALANCE_THRESHOLD = float(os.getenv("LOW_BALANCE_THRESHOLD", "500"))


async def run(redis_client, user_ids: list[str] | None = None) -> list[dict]:
    """
    Check account balances for all (or specified) users.
    Publishes a LOW_BALANCE event when balance < LOW_BALANCE_THRESHOLD.

    Returns list of events produced this run.
    """
    events: list[dict] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # The transactions service exposes a summary endpoint
            response = await client.get(f"{TRANSACTIONS_SERVICE_URL}/balances/summary")
            if response.status_code != 200:
                log.warning("transactions-service returned %s", response.status_code)
                return events

            data = response.json()
            balances = data.get("balances", [])

        except httpx.RequestError as exc:
            log.error("Could not reach transactions-service: %s", exc)
            return events

    for item in balances:
        uid = item.get("user_id")
        if user_ids and uid not in user_ids:
            continue

        balance = float(item.get("available_balance", 0))

        # Cache latest balance in Redis
        await redis_client.hset(
            f"finops:balance:{uid}",
            mapping={
                "available_balance": balance,
                "currency":          item.get("currency", "GBP"),
                "updated_at":        datetime.now(timezone.utc).isoformat(),
            },
        )

        if balance < LOW_BALANCE_THRESHOLD:
            event = {
                "type":              EventType.LOW_BALANCE,
                "user_id":           uid,
                "available_balance": balance,
                "threshold":         LOW_BALANCE_THRESHOLD,
                "currency":          item.get("currency", "GBP"),
                "checked_at":        datetime.now(timezone.utc).isoformat(),
            }
            events.append(event)
            await publish_event(redis_client, stream="finops:alerts", event=event)
            log.info(
                "LOW BALANCE alert for user %s: £%.2f (threshold £%.2f)",
                uid, balance, LOW_BALANCE_THRESHOLD,
            )

    return events
