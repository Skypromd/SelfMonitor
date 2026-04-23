"""Monthly Road to mortgage summary email + optional Expo push (roadmap 1.5.6)."""

from __future__ import annotations

import logging
from datetime import date
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


def _smtp_ready() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _format_digest_body(data: dict[str, Any], *, month_label: str) -> tuple[str, str]:
    step_id, title = parse_current_step_id_and_title(data)
    label = (title or (step_id or "progress").replace("_", " ").title()) if step_id else "Road to mortgage"
    lines: list[str] = []
    steps = data.get("steps")
    if isinstance(steps, list):
        for row in steps:
            if not isinstance(row, dict):
                continue
            t = row.get("title")
            st = row.get("status")
            if isinstance(t, str) and t.strip() and isinstance(st, str):
                lines.append(f"  - {t.strip()}: {st}")
    body = (
        f"Hello,\n\n"
        f"Road to mortgage summary ({month_label}).\n"
        f"Current focus: {label}.\n\n"
    )
    if lines:
        body += "Steps:\n" + "\n".join(lines[:10]) + "\n\n"
    est = data.get("estimated_months_to_deposit_goal")
    if isinstance(est, int) and est > 0:
        body += f"Illustrative months to deposit goal: about {est}.\n\n"
    body += (
        "Open MyNetTax -> Reports -> Road to mortgage for details "
        "(informational only, not lending advice).\n\n"
        "- MyNetTax\n"
    )
    subject = "MyNetTax: Road to mortgage monthly check-in"
    return subject, body


async def dispatch_mortgage_monthly_digest(redis: Any) -> dict[str, int]:
    if redis is None:
        return {
            "recipients_checked": 0,
            "emails_sent": 0,
            "pushes_sent": 0,
        }
    emails = await fetch_recipient_emails()
    today = date.today()
    ym = f"{today.year}-{today.month:02d}"
    month_label = today.strftime("%B %Y")
    emails_sent = 0
    pushes_sent = 0
    for addr in emails:
        e = addr.strip().lower()
        dedup = f"mortgage:monthly_digest:{e}:{ym}"
        first = await redis.set(dedup, "1", nx=True, ex=86400 * 50)
        if not first:
            continue
        data = await fetch_mortgage_progress_payload(e)
        if not data:
            await redis.delete(dedup)
            continue
        step_id, _ = parse_current_step_id_and_title(data)
        if not step_id:
            await redis.delete(dedup)
            continue
        subject, body = _format_digest_body(data, month_label=month_label)
        mail_ok = False
        if _smtp_ready():
            try:
                _send_smtp(e, subject, body)
                mail_ok = True
            except Exception as exc:
                log.warning("mortgage monthly digest SMTP failed for %s: %s", e, exc)
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
                log.warning("mortgage monthly digest push failed for %s: %s", e, exc)
                if not mail_ok:
                    await redis.delete(dedup)
                    continue
        if not mail_ok and not push_ok:
            await redis.delete(dedup)
            continue
        if mail_ok:
            emails_sent += 1
        if push_ok:
            pushes_sent += 1
    log.info(
        "mortgage monthly digest: emails=%s pushes=%s checked=%s",
        emails_sent,
        pushes_sent,
        len(emails),
    )
    return {
        "recipients_checked": len(emails),
        "emails_sent": emails_sent,
        "pushes_sent": pushes_sent,
    }
