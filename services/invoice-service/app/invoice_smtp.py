from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER).strip()


def send_client_payment_request_email(
    *,
    to_email: str,
    client_name: str,
    invoice_number: str,
    amount_gbp: float,
    pay_url: str,
) -> None:
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        log.info("skip client payment email: no valid client_email")
        return
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        log.info("SMTP not configured — skip client payment email to %s", to_email)
        return
    subject = f"Pay invoice {invoice_number} — MyNetTax"
    body = (
        f"Hello {client_name},\n\n"
        f"Please pay invoice {invoice_number} for £{amount_gbp:.2f} using this secure link:\n"
        f"{pay_url}\n\n"
        f"Thank you,\nMyNetTax\n"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.sendmail(SMTP_FROM or SMTP_USER, to_email, msg.as_string())
    except Exception as exc:
        log.warning("client payment email failed for %s: %s", to_email, exc)
