"""
Weekly mortgage journey step checks (roadmap 1.5.6).

When analytics `current_step_id` changes vs last stored value, send email + Expo
push (same channels as MTD reminders). First observed step is stored without notify.
"""

from __future__ import annotations

import logging
from typing import Any

from app.marketing.mortgage_progress_client import (
    fetch_mortgage_progress_payload,
    parse_current_step_id_and_title,
)
from app.mtd.expo_push import send_expo_push_notification
from app.mtd.reminder_email import (
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_USER,
    _registered_expo_token,
    _send_smtp,
    fetch_recipient_emails,
)

log = logging.getLogger(__name__)

_STEP_TTL_SECONDS = 400 * 86400
_TRANSITION_DEDUP_SECONDS = 90 * 86400


def _smtp_ready() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _last_step_key(email: str) -> str:
    return f"mortgage:last_step:{email.strip().lower()}"


def _transition_dedup_key(email: str, prev: str, new: str) -> str:
    return f"mortgage:milestone:{email.strip().lower()}:{prev}->{new}"


async def _fetch_current_mortgage_step(user_email: str) -> tuple[str | None, str | None]:
    data = await fetch_mortgage_progress_payload(user_email)
    if not data:
        return None, None
    return parse_current_step_id_and_title(data)


async def dispatch_mortgage_milestone_notifications(redis: Any) -> dict[str, int]:
    """Compare each active user's mortgage current step; notify on change."""
    if redis is None:
        return {
            "recipients_checked": 0,
            "notifications_sent": 0,
            "skipped_baseline": 0,
            "advance_no_channel": 0,
        }
    emails = await fetch_recipient_emails()
    sent = 0
    baseline = 0
    advance_no_channel = 0
    for addr in emails:
        e = addr.strip().lower()
        try:
            new_id, title = await _fetch_current_mortgage_step(e)
        except Exception as exc:
            log.warning("mortgage milestone skip %s: %s", e, exc)
            continue
        if not new_id:
            continue
        key = _last_step_key(e)
        prev_raw = await redis.get(key)
        prev = prev_raw.decode("utf-8") if prev_raw else None
        if prev is None:
            await redis.set(key, new_id, ex=_STEP_TTL_SECONDS)
            baseline += 1
            continue
        if prev == new_id:
            continue
        dedup = _transition_dedup_key(e, prev, new_id)
        first = await redis.set(dedup, "1", nx=True, ex=_TRANSITION_DEDUP_SECONDS)
        if not first:
            await redis.set(key, new_id, ex=_STEP_TTL_SECONDS)
            continue
        label = title or new_id.replace("_", " ").title()
        subject = "MyNetTax: Road to mortgage - next step"
        body = (
            f"Hello,\n\n"
            f"Your suggested focus in MyNetTax has moved to: {label}.\n\n"
            f"Open Reports -> Road to mortgage for the full timeline (informational only, not lending advice).\n\n"
            f"- MyNetTax\n"
        )
        mail_ok = False
        if _smtp_ready():
            try:
                _send_smtp(e, subject, body)
                mail_ok = True
            except Exception as exc:
                log.warning("mortgage milestone SMTP failed for %s: %s", e, exc)
                await redis.delete(dedup)
                continue

        token = await _registered_expo_token(redis, e)
        push_ok = False
        if token:
            try:
                short = " ".join(body.split())[:280]
                await send_expo_push_notification(
                    to_token=token,
                    title=subject,
                    body=short,
                )
                push_ok = True
            except Exception as exc:
                log.warning("mortgage milestone push failed for %s: %s", e, exc)
                if not mail_ok:
                    await redis.delete(dedup)
                    continue

        if not mail_ok and not push_ok:
            await redis.set(key, new_id, ex=_STEP_TTL_SECONDS)
            advance_no_channel += 1
            continue

        await redis.set(key, new_id, ex=_STEP_TTL_SECONDS)
        sent += 1
    log.info(
        "mortgage milestone digest: sent=%s baseline=%s no_channel=%s checked=%s",
        sent,
        baseline,
        advance_no_channel,
        len(emails),
    )
    return {
        "recipients_checked": len(emails),
        "notifications_sent": sent,
        "skipped_baseline": baseline,
        "advance_no_channel": advance_no_channel,
    }
