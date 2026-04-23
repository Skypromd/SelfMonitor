from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

FINOPS_MONITOR_URL = os.getenv("FINOPS_MONITOR_URL", "http://finops-monitor:8021").rstrip("/")
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()


async def notify_seller_invoice_paid(
    *,
    user_id: str,
    invoice_id: str,
    invoice_number: str,
    amount_gbp: str,
    checkout_session_id: str,
) -> None:
    if not INTERNAL_SERVICE_SECRET:
        return
    payload: dict[str, Any] = {
        "user_id": user_id,
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "amount_gbp": amount_gbp,
        "checkout_session_id": checkout_session_id,
    }
    url = f"{FINOPS_MONITOR_URL}/internal/notify-invoice-paid"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                url,
                json=payload,
                headers={"X-Internal-Token": INTERNAL_SERVICE_SECRET},
            )
            r.raise_for_status()
    except Exception as exc:
        log.warning("invoice-paid notify to finops failed: %s", exc)
