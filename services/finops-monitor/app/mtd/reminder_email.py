"""
MTD ITSA quarterly submission deadline reminders (roadmap §1.4).

Email (SMTP) + Expo push for the same schedule: 14, 7, 3, and 1 day before the
next HMRC deadline, plus urgent notice from 1 day before through deadline day if
the quarter is not marked submitted.
"""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from typing import Any

import httpx

from app.mtd.auto_draft import try_mtd_auto_draft_for_upcoming_deadline
from app.mtd.deadlines import get_next_deadline
from app.mtd.tracker import QuarterlyAccumulator
from app.redis_bus import publish_event

log = logging.getLogger(__name__)

REMINDER_TIERS = (14, 7, 3, 1)
_DEDUP_TTL_SECONDS = 60 * 60 * 24 * 90

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER).strip()

INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()
AUTH_SERVICE_INTERNAL_URL = os.getenv(
    "AUTH_SERVICE_INTERNAL_URL", "http://auth-service:80"
).strip()


async def fetch_recipient_emails() -> list[str]:
    if not INTERNAL_SERVICE_SECRET:
        log.warning("INTERNAL_SERVICE_SECRET unset — cannot load reminder recipients")
        return []
    url = f"{AUTH_SERVICE_INTERNAL_URL.rstrip('/')}/internal/reminder-recipients"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            url,
            headers={"X-Internal-Token": INTERNAL_SERVICE_SECRET},
        )
        response.raise_for_status()
        payload = response.json()
    raw = payload.get("emails") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []
    return sorted({str(e).strip().lower() for e in raw if e and "@" in str(e)})


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        log.info("SMTP not configured — would email %s: %s", to_email, subject)
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_FROM or SMTP_USER, to_email, msg.as_string())


def _email_dedup_key(user_id: str, deadline: date, kind: str) -> str:
    return f"mtd:reminder_email:{user_id}:{deadline.isoformat()}:{kind}"


_dedup_key = _email_dedup_key


def _push_dedup_key(user_id: str, deadline: date, kind: str) -> str:
    return f"mtd:reminder_push:{user_id}:{deadline.isoformat()}:{kind}"


async def _try_send_email(
    redis: Any,
    *,
    user_id: str,
    deadline: date,
    kind: str,
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    key = _email_dedup_key(user_id, deadline, kind)
    first = await redis.set(key, "1", nx=True, ex=_DEDUP_TTL_SECONDS)
    if not first:
        return False
    try:
        _send_smtp(to_email, subject, body)
    except Exception as exc:
        log.warning("MTD reminder SMTP failed for %s: %s", to_email, exc)
        await redis.delete(key)
        return False
    return True


async def _registered_expo_token(redis: Any, user_id: str) -> str | None:
    raw = await redis.get(f"mtd:expo_push:{user_id.strip().lower()}")
    if not raw:
        return None
    return str(raw).strip() or None


async def _try_send_push(
    redis: Any,
    *,
    user_id: str,
    deadline: date,
    kind: str,
    expo_token: str,
    title: str,
    body: str,
) -> bool:
    from app.mtd.expo_push import send_expo_push_notification

    key = _push_dedup_key(user_id, deadline, kind)
    first = await redis.set(key, "1", nx=True, ex=_DEDUP_TTL_SECONDS)
    if not first:
        return False
    short_body = " ".join(body.split())[:280]
    try:
        await send_expo_push_notification(
            to_token=expo_token, title=title, body=short_body
        )
    except Exception as exc:
        log.warning("MTD reminder Expo push failed for %s: %s", user_id, exc)
        await redis.delete(key)
        return False
    return True


async def _send_reminder_channels(
    redis: Any,
    *,
    user_id: str,
    to_email: str,
    deadline: date,
    kind: str,
    subject: str,
    body: str,
    next_q_label: str,
    extra_event: dict[str, Any] | None = None,
) -> None:
    sent_mail = await _try_send_email(
        redis,
        user_id=user_id,
        deadline=deadline,
        kind=kind,
        to_email=to_email,
        subject=subject,
        body=body,
    )
    if sent_mail:
        event_type = (
            "mtd_deadline_urgent_email"
            if kind == "urgent-pending"
            else "mtd_deadline_email"
        )
        ev: dict[str, Any] = {
            "type": event_type,
            "deadline": deadline.isoformat(),
            "quarter": next_q_label,
        }
        if extra_event:
            ev.update(extra_event)
        await publish_event(redis, f"finops:mtd:{user_id}", ev)

    expo = await _registered_expo_token(redis, user_id)
    if expo:
        push_sent = await _try_send_push(
            redis,
            user_id=user_id,
            deadline=deadline,
            kind=kind,
            expo_token=expo,
            title=subject,
            body=body,
        )
        if push_sent:
            pe: dict[str, Any] = {
                "type": "mtd_deadline_push",
                "kind": kind,
                "deadline": deadline.isoformat(),
                "quarter": next_q_label,
            }
            if extra_event:
                pe.update(extra_event)
            await publish_event(redis, f"finops:mtd:{user_id}", pe)


async def process_user_day(
    redis: Any,
    user_id: str,
    to_email: str,
    today: date | None = None,
) -> None:
    today = today or date.today()
    next_q = get_next_deadline(today)
    deadline = next_q.submission_deadline
    days_left = (deadline - today).days
    acc = QuarterlyAccumulator(redis, user_id)
    quarter_data = await acc.get(next_q)
    status = str(quarter_data.get("status") or "")

    for tier in REMINDER_TIERS:
        if days_left != tier:
            continue
        if status == "submitted":
            continue
        subject = f"MyNetTax: MTD quarterly update due in {tier} day(s)"
        body = (
            f"Hello,\n\n"
            f"This is a reminder that your next MTD for Income Tax quarterly update "
            f"({next_q.label}) must be submitted by {deadline.isoformat()}.\n\n"
            f"You have {tier} day(s) left.\n\n"
        )
        extra: dict[str, Any] = {"tier": tier}
        if tier == 3:
            body += (
                "You can now review your figures in MyNetTax and prepare your quarterly "
                "summary as a draft. Nothing is sent to HMRC until you explicitly confirm "
                "each submission step.\n\n"
            )
            extra["mtd_draft_prep_hint"] = True
        body += "— MyNetTax\n"
        await _send_reminder_channels(
            redis,
            user_id=user_id,
            to_email=to_email,
            deadline=deadline,
            kind=f"tier-{tier}",
            subject=subject,
            body=body,
            next_q_label=next_q.label,
            extra_event=extra,
        )
        if tier == 3:
            await try_mtd_auto_draft_for_upcoming_deadline(
                redis,
                user_id=user_id,
                next_q_label=next_q.label,
                deadline=deadline,
                days_before_deadline=tier,
            )

    if days_left <= 1 and status != "submitted":
        subject = "Urgent: MTD quarterly update — action needed"
        body = (
            f"Hello,\n\n"
            f"Your MTD quarterly update ({next_q.label}) is due by {deadline.isoformat()}. "
            f"We do not see it marked as submitted yet.\n\n"
            f"Please complete your submission in HMRC / MyNetTax as soon as possible.\n\n"
            f"— MyNetTax\n"
        )
        await _send_reminder_channels(
            redis,
            user_id=user_id,
            to_email=to_email,
            deadline=deadline,
            kind="urgent-pending",
            subject=subject,
            body=body,
            next_q_label=next_q.label,
            extra_event={"status": status},
        )


async def dispatch_daily_reminders(redis: Any) -> dict[str, int]:
    """Load recipients from auth-service and send due reminders (idempotent via Redis)."""
    emails = await fetch_recipient_emails()
    processed = 0
    for addr in emails:
        try:
            await process_user_day(redis, user_id=addr, to_email=addr)
            processed += 1
        except Exception as exc:
            log.warning("reminder skip for %s: %s", addr, exc)
    log.info("MTD deadline reminders finished for %s user(s)", processed)
    return {"recipients_checked": processed}
