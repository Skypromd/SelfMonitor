from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.mtd.reminder_email import _send_smtp, fetch_recipient_emails

log = logging.getLogger(__name__)


async def dispatch_referral_invite_emails(redis: Any) -> dict[str, int]:
    """Monthly campaign: invite a friend, £25 credit (dedup per user per month)."""
    if not redis:
        log.warning("referral invite: redis unavailable")
        return {"recipients_checked": 0, "emails_sent": 0}
    emails = await fetch_recipient_emails()
    today = date.today()
    ym = f"{today.year}-{today.month:02d}"
    sent = 0
    for addr in emails:
        if not redis:
            break
        key = f"marketing:referral_invite:{addr.lower()}:{ym}"
        first = await redis.set(key, "1", nx=True, ex=86400 * 45)
        if not first:
            continue
        subject = "Invite a friend to MyNetTax — £25 credit each"
        body = (
            f"Hello,\n\n"
            f"Share your referral link from the MyNetTax app — when a friend joins, "
            f"you each receive £25 account credit toward your subscription.\n\n"
            f"— MyNetTax\n"
        )
        try:
            _send_smtp(addr, subject, body)
            sent += 1
        except Exception as exc:
            log.warning("referral invite email failed for %s: %s", addr, exc)
            await redis.delete(key)
    log.info("referral invite campaign: sent=%s checked=%s", sent, len(emails))
    return {"recipients_checked": len(emails), "emails_sent": sent}
