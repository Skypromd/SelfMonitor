"""
Invoice monitor — checks for overdue and soon-due invoices and publishes alerts.

invoice-service: internal port 8015 (or $INVOICE_SERVICE_URL).
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone

import httpx

from app.redis_bus import EventType, publish_event

log = logging.getLogger(__name__)

INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://invoice-service:8015")

# Warn when an invoice is due within this many days
INVOICE_WARNING_DAYS = int(os.getenv("INVOICE_WARNING_DAYS", "7"))


async def run(redis_client, user_ids: list[str] | None = None) -> list[dict]:
    """
    Check for overdue and soon-due invoices.
    Publishes INVOICE_OVERDUE / INVOICE_DUE_SOON events to Redis.

    Returns list of events produced this run.
    """
    events: list[dict] = []
    today = date.today()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{INVOICE_SERVICE_URL}/invoices",
                params={"status": "unpaid"},
            )
            if response.status_code != 200:
                log.warning("invoice-service returned %s", response.status_code)
                return events

            data = response.json()
            invoices = data.get("invoices", [])

        except httpx.RequestError as exc:
            log.error("Could not reach invoice-service: %s", exc)
            return events

    for inv in invoices:
        uid = inv.get("user_id")
        if user_ids and uid not in user_ids:
            continue

        due_str = inv.get("due_date")
        if not due_str:
            continue

        try:
            due_date = date.fromisoformat(due_str[:10])
        except ValueError:
            log.warning("Invalid due_date %s on invoice %s", due_str, inv.get("id"))
            continue

        days_left = (due_date - today).days

        if days_left < 0:
            event_type = EventType.INVOICE_OVERDUE
            severity = "high"
        elif days_left <= INVOICE_WARNING_DAYS:
            event_type = EventType.INVOICE_DUE_SOON
            severity = "medium"
        else:
            continue   # not due yet

        event = {
            "type":       event_type,
            "user_id":    uid,
            "invoice_id": inv.get("id"),
            "amount":     inv.get("total_amount"),
            "currency":   inv.get("currency", "GBP"),
            "client":     inv.get("client_name"),
            "due_date":   due_str,
            "days_left":  days_left,
            "severity":   severity,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        events.append(event)
        await publish_event(redis_client, stream="finops:alerts", event=event)
        log.info(
            "%s for user %s invoice %s (due %s, %d days)",
            event_type, uid, event["invoice_id"], due_str, days_left,
        )

    return events
