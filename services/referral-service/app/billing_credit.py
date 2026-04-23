from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

BILLING_SERVICE_URL = os.getenv("BILLING_SERVICE_URL", "http://billing-service:80").rstrip("/")
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()


async def grant_referral_pair_credits(
    *,
    referrer_user_id: str,
    referee_user_id: str,
    amount_gbp: float,
    usage_id: str,
) -> None:
    if not INTERNAL_SERVICE_SECRET or amount_gbp <= 0:
        return
    url = f"{BILLING_SERVICE_URL}/internal/account-credit"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_SECRET}
    async with httpx.AsyncClient(timeout=25.0) as client:
        for suffix, email in (
            ("referrer", referrer_user_id.strip().lower()),
            ("referee", referee_user_id.strip().lower()),
        ):
            if "@" not in email:
                continue
            payload: dict[str, Any] = {
                "email": email,
                "amount_gbp": amount_gbp,
                "idempotency_key": f"referral-{usage_id}-{suffix}",
                "reason": f"referral_{suffix}",
            }
            try:
                r = await client.post(url, json=payload, headers=headers)
                r.raise_for_status()
            except Exception as exc:
                log.warning("billing credit failed (%s): %s", suffix, exc)
