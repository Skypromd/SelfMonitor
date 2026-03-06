"""
Fraud monitor — polls the fraud-detection service and publishes alerts.

fraud-detection service: internal port 8013 (or $FRAUD_SERVICE_URL).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from app.redis_bus import publish_event, EventType

log = logging.getLogger(__name__)

FRAUD_SERVICE_URL = os.getenv("FRAUD_SERVICE_URL", "http://fraud-detection-service:8013")


async def run(redis_client, user_ids: list[str] | None = None) -> list[dict]:
    """
    Check recent transactions for fraud across all (or specified) users.
    Publishes an alert event to Redis for each flagged transaction.

    Returns list of alert dicts produced this run.
    """
    alerts: list[dict] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Fetch recent fraud alerts from the fraud-detection service
            response = await client.get(f"{FRAUD_SERVICE_URL}/alerts/recent")
            if response.status_code != 200:
                log.warning("fraud-detection returned %s", response.status_code)
                return alerts

            data = response.json()
            flagged = data.get("alerts", [])

        except httpx.RequestError as exc:
            log.error("Could not reach fraud-detection service: %s", exc)
            return alerts

    for item in flagged:
        uid = item.get("user_id")
        if user_ids and uid not in user_ids:
            continue

        alert = {
            "type":           EventType.FRAUD_ALERT,
            "user_id":        uid,
            "transaction_id": item.get("transaction_id"),
            "amount":         item.get("amount"),
            "reason":         item.get("reason", "unknown"),
            "score":          item.get("fraud_score", 0),
            "detected_at":    item.get("detected_at") or datetime.now(timezone.utc).isoformat(),
        }
        alerts.append(alert)

        await publish_event(redis_client, stream="finops:alerts", event=alert)
        log.info("FRAUD ALERT published for user %s tx %s", uid, alert["transaction_id"])

    return alerts
