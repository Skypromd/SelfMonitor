from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.mtd.expo_push import send_expo_push_notification
from app.mtd.reminder_email import _registered_expo_token, fetch_recipient_emails

log = logging.getLogger(__name__)


async def dispatch_tax_savings_monthly_push(redis: Any) -> dict[str, int]:
    """Monthly Expo push: open Tax-saving ideas on tax preparation (roadmap 2.5)."""
    if not redis:
        return {"pushes_sent": 0, "recipients_checked": 0}
    emails = await fetch_recipient_emails()
    today = date.today()
    ym = f"{today.year}-{today.month:02d}"
    sent = 0
    for addr in emails:
        key = f"tax_tips:monthly_push:{addr.lower()}:{ym}"
        first = await redis.set(key, "1", nx=True, ex=86400 * 45)
        if not first:
            continue
        token = await _registered_expo_token(redis, addr)
        if not token:
            await redis.delete(key)
            continue
        try:
            await send_expo_push_notification(
                to_token=token,
                title="Tax-saving ideas for you",
                body="Review personalised UK tax tips in MyNetTax → Tax preparation.",
            )
            sent += 1
        except Exception as exc:
            log.warning("tax tips monthly push failed for %s: %s", addr, exc)
            await redis.delete(key)
    log.info("tax savings monthly push: sent=%s checked=%s", sent, len(emails))
    return {"recipients_checked": len(emails), "pushes_sent": sent}
