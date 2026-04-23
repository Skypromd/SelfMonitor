from __future__ import annotations

import logging
from typing import Any

from app.mtd.expo_push import send_expo_push_notification
from app.mtd.reminder_email import _registered_expo_token, _send_smtp
from app.redis_bus import EventType, publish_event

log = logging.getLogger(__name__)

_DEDUP_TTL = 60 * 60 * 24 * 60


async def handle_invoice_paid_notify(
    redis: Any,
    *,
    user_id: str,
    invoice_id: str,
    invoice_number: str,
    amount_gbp: str,
    checkout_session_id: str,
) -> dict[str, Any]:
    to_email = user_id.strip() if "@" in user_id else ""
    if not to_email:
        return {"skipped": True, "reason": "no_seller_email"}

    dedup = checkout_session_id.strip() or f"noid:{invoice_id}"
    key = f"invoice:seller_paid_notify:{dedup}"
    if redis:
        first = await redis.set(key, "1", nx=True, ex=_DEDUP_TTL)
        if not first:
            return {"skipped": True, "reason": "duplicate"}

    subject = f"Invoice {invoice_number} paid — £{amount_gbp} received"
    body = (
        f"Good news — you received £{amount_gbp} for invoice {invoice_number} "
        f"(paid via Stripe).\n\n— MyNetTax\n"
    )
    try:
        _send_smtp(to_email, subject, body)
    except Exception as exc:
        log.warning("invoice paid seller email failed: %s", exc)
        if redis:
            await redis.delete(key)
        return {"email_sent": False, "error": str(exc)[:200]}

    if redis:
        await publish_event(
            redis,
            stream=f"finops:mtd:{user_id}",
            event={
                "type": EventType.INVOICE_PAID,
                "invoice_number": invoice_number,
                "amount_gbp": amount_gbp,
                "invoice_id": invoice_id,
            },
        )

    expo = await _registered_expo_token(redis, user_id)
    if expo:
        try:
            await send_expo_push_notification(
                to_token=expo,
                title=subject[:180],
                body=f"£{amount_gbp} received for {invoice_number}.",
            )
        except Exception as exc:
            log.warning("invoice paid seller push failed: %s", exc)

    return {"email_sent": True, "push_attempted": bool(expo)}
