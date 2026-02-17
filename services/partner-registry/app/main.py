import asyncio
import datetime
import csv
import io
import math
import os
import sys
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text

from . import crud, models, schemas
from .database import AsyncSessionLocal, Base, engine, get_db

COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")
AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "false").lower() == "true"

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import (
    DEFAULT_ALGORITHM,
    DEFAULT_SECRET_KEY,
    build_jwt_auth_dependencies,
)
from libs.shared_http.retry import post_json_with_retry

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", DEFAULT_SECRET_KEY)
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", DEFAULT_ALGORITHM)
BILLING_REPORT_ALLOWED_USERS = {
    item.strip()
    for item in os.getenv("BILLING_REPORT_ALLOWED_USERS", "").split(",")
    if item.strip()
}
BILLING_REPORT_ALLOWED_SCOPES = {
    item.strip()
    for item in os.getenv("BILLING_REPORT_ALLOWED_SCOPES", "billing:read").split(",")
    if item.strip()
}
BILLING_REPORT_ALLOWED_ROLES = {
    item.strip()
    for item in os.getenv("BILLING_REPORT_ALLOWED_ROLES", "admin,billing_admin").split(",")
    if item.strip()
}
DEFAULT_BILLABLE_STATUSES = [schemas.LeadStatus.qualified.value]
DEFAULT_BILLING_STATUSES = [
    schemas.LeadStatus.qualified.value,
    schemas.LeadStatus.converted.value,
]


def _parse_positive_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _parse_non_negative_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


BILLING_INVOICE_DUE_DAYS = _parse_positive_int_env("BILLING_INVOICE_DUE_DAYS", 14)
SELF_EMPLOYED_INVOICE_DUE_DAYS = _parse_positive_int_env("SELF_EMPLOYED_INVOICE_DUE_DAYS", 14)
SELF_EMPLOYED_PAYMENT_LINK_BASE_URL = os.getenv(
    "SELF_EMPLOYED_PAYMENT_LINK_BASE_URL",
    "https://pay.selfmonitor.app/invoices",
).rstrip("/")
SELF_EMPLOYED_PAYMENT_LINK_PROVIDER = os.getenv(
    "SELF_EMPLOYED_PAYMENT_LINK_PROVIDER",
    "selfmonitor_payment_link",
)
SELF_EMPLOYED_REMINDER_DUE_SOON_DAYS = _parse_positive_int_env("SELF_EMPLOYED_REMINDER_DUE_SOON_DAYS", 3)
SELF_EMPLOYED_REMINDER_EMAIL_ENABLED = _parse_bool_env("SELF_EMPLOYED_REMINDER_EMAIL_ENABLED", False)
SELF_EMPLOYED_REMINDER_SMS_ENABLED = _parse_bool_env("SELF_EMPLOYED_REMINDER_SMS_ENABLED", False)
SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER = os.getenv("SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER", "webhook").strip().lower()
SELF_EMPLOYED_REMINDER_SMS_PROVIDER = os.getenv("SELF_EMPLOYED_REMINDER_SMS_PROVIDER", "webhook").strip().lower()
SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL = os.getenv("SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL", "").strip()
SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL = os.getenv("SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL", "").strip()
SELF_EMPLOYED_REMINDER_EMAIL_FROM = os.getenv("SELF_EMPLOYED_REMINDER_EMAIL_FROM", "noreply@selfmonitor.app").strip()
SELF_EMPLOYED_REMINDER_SMS_FROM = os.getenv("SELF_EMPLOYED_REMINDER_SMS_FROM", "SelfMonitor").strip()
SELF_EMPLOYED_SENDGRID_API_URL = os.getenv("SELF_EMPLOYED_SENDGRID_API_URL", "https://api.sendgrid.com/v3/mail/send").strip()
SELF_EMPLOYED_SENDGRID_API_KEY = os.getenv("SELF_EMPLOYED_SENDGRID_API_KEY", "").strip()
SELF_EMPLOYED_TWILIO_API_BASE_URL = os.getenv("SELF_EMPLOYED_TWILIO_API_BASE_URL", "https://api.twilio.com").strip().rstrip("/")
SELF_EMPLOYED_TWILIO_ACCOUNT_SID = os.getenv("SELF_EMPLOYED_TWILIO_ACCOUNT_SID", "").strip()
SELF_EMPLOYED_TWILIO_AUTH_TOKEN = os.getenv("SELF_EMPLOYED_TWILIO_AUTH_TOKEN", "").strip()
SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID = os.getenv("SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID", "").strip()
SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS = _parse_positive_int_env("SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS", 3)
SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_BASE_DELAY_SECONDS = max(
    _parse_non_negative_float_env("SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_BASE_DELAY_SECONDS", 0.5),
    0.05,
)
SELF_EMPLOYED_REMINDER_DISPATCH_TIMEOUT_SECONDS = max(
    _parse_non_negative_float_env("SELF_EMPLOYED_REMINDER_DISPATCH_TIMEOUT_SECONDS", 5.0),
    0.1,
)
SELF_EMPLOYED_CALENDAR_REMINDER_COOLDOWN_HOURS = _parse_positive_int_env(
    "SELF_EMPLOYED_CALENDAR_REMINDER_COOLDOWN_HOURS",
    12,
)
SELF_EMPLOYED_CALENDAR_AUTORUN_ENABLED = _parse_bool_env("SELF_EMPLOYED_CALENDAR_AUTORUN_ENABLED", False)
SELF_EMPLOYED_CALENDAR_AUTORUN_INTERVAL_SECONDS = _parse_positive_int_env(
    "SELF_EMPLOYED_CALENDAR_AUTORUN_INTERVAL_SECONDS",
    300,
)
SELF_EMPLOYED_CALENDAR_AUTORUN_HORIZON_HOURS = _parse_positive_int_env(
    "SELF_EMPLOYED_CALENDAR_AUTORUN_HORIZON_HOURS",
    24,
)
SELF_EMPLOYED_CALENDAR_AUTORUN_USER_BATCH = _parse_positive_int_env(
    "SELF_EMPLOYED_CALENDAR_AUTORUN_USER_BATCH",
    500,
)
LEAD_STATUS_TRANSITIONS = {
    schemas.LeadStatus.initiated.value: {schemas.LeadStatus.qualified.value, schemas.LeadStatus.rejected.value},
    schemas.LeadStatus.qualified.value: {schemas.LeadStatus.converted.value, schemas.LeadStatus.rejected.value},
    schemas.LeadStatus.rejected.value: set(),
    schemas.LeadStatus.converted.value: set(),
}
INVOICE_STATUS_TRANSITIONS = {
    schemas.BillingInvoiceStatus.generated.value: {
        schemas.BillingInvoiceStatus.issued.value,
        schemas.BillingInvoiceStatus.void.value,
    },
    schemas.BillingInvoiceStatus.issued.value: {
        schemas.BillingInvoiceStatus.paid.value,
        schemas.BillingInvoiceStatus.void.value,
    },
    schemas.BillingInvoiceStatus.paid.value: set(),
    schemas.BillingInvoiceStatus.void.value: set(),
}
SELF_EMPLOYED_INVOICE_STATUS_TRANSITIONS = {
    schemas.SelfEmployedInvoiceStatus.draft.value: {
        schemas.SelfEmployedInvoiceStatus.issued.value,
        schemas.SelfEmployedInvoiceStatus.void.value,
    },
    schemas.SelfEmployedInvoiceStatus.issued.value: {
        schemas.SelfEmployedInvoiceStatus.paid.value,
        schemas.SelfEmployedInvoiceStatus.overdue.value,
        schemas.SelfEmployedInvoiceStatus.void.value,
    },
    schemas.SelfEmployedInvoiceStatus.overdue.value: {
        schemas.SelfEmployedInvoiceStatus.paid.value,
        schemas.SelfEmployedInvoiceStatus.void.value,
    },
    schemas.SelfEmployedInvoiceStatus.paid.value: set(),
    schemas.SelfEmployedInvoiceStatus.void.value: set(),
}

SEED_READINESS_MIN_PERIOD_MONTHS = 3
SEED_READINESS_MAX_PERIOD_MONTHS = 24
PMF_MIN_COHORT_MONTHS = 3
PMF_MAX_COHORT_MONTHS = 24
PMF_MIN_ACTIVATION_WINDOW_DAYS = 7
PMF_MAX_ACTIVATION_WINDOW_DAYS = 60
NPS_MIN_PERIOD_MONTHS = 3
NPS_MAX_PERIOD_MONTHS = 24
PMF_GATE_REQUIRED_ACTIVATION_RATE_PERCENT = _parse_non_negative_float_env(
    "PMF_GATE_REQUIRED_ACTIVATION_RATE_PERCENT",
    60.0,
)
PMF_GATE_REQUIRED_RETENTION_90D_PERCENT = _parse_non_negative_float_env(
    "PMF_GATE_REQUIRED_RETENTION_90D_PERCENT",
    75.0,
)
PMF_GATE_REQUIRED_NPS_SCORE = _parse_non_negative_float_env(
    "PMF_GATE_REQUIRED_NPS_SCORE",
    45.0,
)
PMF_GATE_MIN_ELIGIBLE_USERS_90D = _parse_positive_int_env("PMF_GATE_MIN_ELIGIBLE_USERS_90D", 20)
PMF_GATE_MIN_NPS_RESPONSES = _parse_positive_int_env("PMF_GATE_MIN_NPS_RESPONSES", 20)
UNIT_ECONOMICS_MIN_PERIOD_MONTHS = 3
UNIT_ECONOMICS_MAX_PERIOD_MONTHS = 24
SEED_GATE_REQUIRED_MRR_GBP = _parse_non_negative_float_env("SEED_GATE_REQUIRED_MRR_GBP", 40_000.0)
SEED_GATE_MAX_MONTHLY_CHURN_PERCENT = _parse_non_negative_float_env("SEED_GATE_MAX_MONTHLY_CHURN_PERCENT", 3.0)
SEED_GATE_MIN_LTV_CAC_RATIO = _parse_non_negative_float_env("SEED_GATE_MIN_LTV_CAC_RATIO", 4.0)


def _claims_to_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {item.strip() for item in value.replace(",", " ").split() if item.strip()}
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def require_billing_report_access(token: str = Depends(get_bearer_token)) -> str:
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    if user_id in BILLING_REPORT_ALLOWED_USERS:
        return str(user_id)

    scopes = _claims_to_set(payload.get("scopes"))
    roles = _claims_to_set(payload.get("roles"))
    is_admin = payload.get("is_admin") is True

    if is_admin or scopes.intersection(BILLING_REPORT_ALLOWED_SCOPES) or roles.intersection(BILLING_REPORT_ALLOWED_ROLES):
        return str(user_id)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for lead reports",
    )

@asynccontextmanager
async def lifespan(_app: FastAPI):
    background_task: asyncio.Task[None] | None = None
    if AUTO_CREATE_SCHEMA:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        if not AUTO_CREATE_SCHEMA:
            try:
                await db.execute(text("SELECT 1 FROM partners LIMIT 1"))
            except Exception as exc:
                raise RuntimeError(
                    "Partner Registry schema is not initialized. "
                    "Run `alembic upgrade head` or set AUTO_CREATE_SCHEMA=true for local bootstrapping."
                ) from exc
        await crud.seed_partners_if_empty(db)
    if SELF_EMPLOYED_CALENDAR_AUTORUN_ENABLED:
        background_task = asyncio.create_task(_calendar_autoreminders_loop())
    try:
        yield
    finally:
        if background_task:
            background_task.cancel()
            with suppress(asyncio.CancelledError):
                await background_task


app = FastAPI(
    title="Partner Registry Service",
    description="Manages a registry of third-party partners.",
    version="1.0.0",
    lifespan=lifespan,
)


async def log_audit_event(user_id: str, action: str, details: Dict[str, Any]) -> str | None:
    try:
        response_data = await post_json_with_retry(
            COMPLIANCE_SERVICE_URL,
            json_body={"user_id": user_id, "action": action, "details": details},
            timeout=5.0,
        )
        return response_data.get("id") if isinstance(response_data, dict) else None
    except httpx.HTTPError as exc:
        print(f"Error: Could not log audit event to compliance service: {exc}")
        return None


async def _run_calendar_autoreminders_pass() -> None:
    async with AsyncSessionLocal() as db:
        user_ids = await crud.list_calendar_users_with_scheduled_events(
            db,
            limit=SELF_EMPLOYED_CALENDAR_AUTORUN_USER_BATCH,
        )
    for user_id in user_ids:
        try:
            async with AsyncSessionLocal() as db:
                await _run_calendar_reminders_for_user(
                    db,
                    user_id=user_id,
                    horizon_hours=SELF_EMPLOYED_CALENDAR_AUTORUN_HORIZON_HOURS,
                    source="scheduler",
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            print(f"Calendar auto-reminder pass failed for user {user_id}: {exc}")


async def _calendar_autoreminders_loop() -> None:
    while True:
        try:
            await _run_calendar_autoreminders_pass()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            print(f"Calendar auto-reminder loop failed: {exc}")
        await asyncio.sleep(SELF_EMPLOYED_CALENDAR_AUTORUN_INTERVAL_SECONDS)


def _build_report_window(
    start_date: datetime.date | None,
    end_date: datetime.date | None,
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    start_at = (
        datetime.datetime.combine(start_date, datetime.time.min, tzinfo=datetime.UTC)
        if start_date
        else None
    )
    end_before = (
        datetime.datetime.combine(
            end_date + datetime.timedelta(days=1),
            datetime.time.min,
            tzinfo=datetime.UTC,
        )
        if end_date
        else None
    )
    return start_at, end_before


def _month_start(date_value: datetime.date) -> datetime.date:
    return datetime.date(date_value.year, date_value.month, 1)


def _shift_month(date_value: datetime.date, delta_months: int) -> datetime.date:
    month_index = (date_value.year * 12) + (date_value.month - 1) + delta_months
    year = month_index // 12
    month = (month_index % 12) + 1
    return datetime.date(year, month, 1)


def _month_key(date_value: datetime.date) -> str:
    return date_value.strftime("%Y-%m")


def _next_cadence_date(
    *,
    date_value: datetime.date,
    cadence: schemas.SelfEmployedRecurringCadence,
) -> datetime.date:
    if cadence == schemas.SelfEmployedRecurringCadence.weekly:
        return date_value + datetime.timedelta(days=7)
    if cadence == schemas.SelfEmployedRecurringCadence.quarterly:
        return _shift_month(_month_start(date_value), 3).replace(day=min(date_value.day, 28))
    return _shift_month(_month_start(date_value), 1).replace(day=min(date_value.day, 28))


def _normalize_brand_accent_color(value: str | None) -> str | None:
    if not value:
        return None
    color = value.strip()
    if not color:
        return None
    if not color.startswith("#"):
        color = f"#{color}"
    if len(color) not in {4, 7}:
        return None
    return color.upper()


def _build_self_employed_payment_link(invoice_id: str) -> str:
    return f"{SELF_EMPLOYED_PAYMENT_LINK_BASE_URL}/{invoice_id}"


def _truncate_text(value: str, *, max_length: int = 500) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _to_utc_datetime(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.UTC)
    return value.astimezone(datetime.UTC)


def _is_retryable_delivery_status(status_code: int) -> bool:
    return status_code in {408, 409, 425, 429, 500, 502, 503, 504}


async def _post_with_delivery_retry(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
) -> httpx.Response:
    last_exception: Exception | None = None
    for attempt in range(1, SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=json_body,
                    data=form_body,
                    auth=auth,
                    timeout=SELF_EMPLOYED_REMINDER_DISPATCH_TIMEOUT_SECONDS,
                )
        except httpx.RequestError as exc:
            last_exception = exc
            if attempt >= SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS:
                raise
            await asyncio.sleep(SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
            continue

        if response.status_code < 400:
            return response
        if _is_retryable_delivery_status(response.status_code) and attempt < SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS:
            await asyncio.sleep(SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
            continue
        raise httpx.HTTPStatusError(
            f"Reminder delivery request failed with status {response.status_code}",
            request=response.request,
            response=response,
        )

    if last_exception is not None:
        raise last_exception
    raise httpx.RequestError("Reminder delivery failed without response.")


def _build_invoice_reminder_email_subject(
    *,
    invoice_number: str,
    reminder_type: Literal["due_soon", "overdue"],
) -> str:
    if reminder_type == "overdue":
        return f"Invoice overdue notice: {invoice_number}"
    return f"Invoice due soon: {invoice_number}"


def _build_invoice_reminder_email_body(
    *,
    invoice_number: str,
    reminder_type: Literal["due_soon", "overdue"],
    message: str,
) -> str:
    lead = (
        f"This is an overdue reminder for invoice {invoice_number}."
        if reminder_type == "overdue"
        else f"This is a due-soon reminder for invoice {invoice_number}."
    )
    return "\n".join([lead, "", message, "", "Sent by SelfMonitor billing automation."])


def _build_invoice_reminder_sms_body(
    *,
    invoice_number: str,
    reminder_type: Literal["due_soon", "overdue"],
    message: str,
) -> str:
    prefix = "OVERDUE" if reminder_type == "overdue" else "DUE SOON"
    raw = f"{prefix}: {invoice_number}. {message}"
    return _truncate_text(raw, max_length=320)


async def _dispatch_invoice_reminder_email(
    *,
    invoice_id: str,
    invoice_number: str,
    reminder_type: Literal["due_soon", "overdue"],
    message: str,
    recipient_email: str | None,
) -> tuple[Literal["sent", "failed"], str]:
    if not SELF_EMPLOYED_REMINDER_EMAIL_ENABLED:
        return "failed", "Email dispatch disabled by configuration."
    if not recipient_email:
        return "failed", "Customer email is missing."
    subject = _build_invoice_reminder_email_subject(invoice_number=invoice_number, reminder_type=reminder_type)
    body = _build_invoice_reminder_email_body(
        invoice_number=invoice_number,
        reminder_type=reminder_type,
        message=message,
    )

    try:
        if SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER == "sendgrid":
            if not SELF_EMPLOYED_SENDGRID_API_KEY:
                return "failed", "SendGrid API key is missing."
            payload = {
                "personalizations": [{"to": [{"email": recipient_email}]}],
                "from": {"email": SELF_EMPLOYED_REMINDER_EMAIL_FROM},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
                "custom_args": {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "reminder_type": reminder_type,
                },
            }
            await _post_with_delivery_retry(
                SELF_EMPLOYED_SENDGRID_API_URL,
                headers={
                    "Authorization": f"Bearer {SELF_EMPLOYED_SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json_body=payload,
            )
            return "sent", f"Email reminder sent via SendGrid to {recipient_email}."

        if SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER == "webhook":
            if not SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL:
                return "failed", "Email dispatch URL is not configured."
            payload = {
                "provider": "self_employed_invoice_reminders",
                "from": SELF_EMPLOYED_REMINDER_EMAIL_FROM,
                "to": recipient_email,
                "subject": subject,
                "message": body,
                "metadata": {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "reminder_type": reminder_type,
                    "dispatch_provider": "webhook",
                },
            }
            await _post_with_delivery_retry(
                SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL,
                json_body=payload,
            )
            return "sent", f"Email reminder sent to {recipient_email}."

        return "failed", f"Unsupported email provider: {SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER}"
    except httpx.HTTPError as exc:
        return "failed", _truncate_text(f"Email dispatch failed: {exc}")


async def _dispatch_invoice_reminder_sms(
    *,
    invoice_id: str,
    invoice_number: str,
    reminder_type: Literal["due_soon", "overdue"],
    message: str,
    recipient_phone: str | None,
) -> tuple[Literal["sent", "failed"], str]:
    if not SELF_EMPLOYED_REMINDER_SMS_ENABLED:
        return "failed", "SMS dispatch disabled by configuration."
    if not recipient_phone:
        return "failed", "Customer phone is missing."
    sms_body = _build_invoice_reminder_sms_body(
        invoice_number=invoice_number,
        reminder_type=reminder_type,
        message=message,
    )

    try:
        if SELF_EMPLOYED_REMINDER_SMS_PROVIDER == "twilio":
            if not SELF_EMPLOYED_TWILIO_ACCOUNT_SID or not SELF_EMPLOYED_TWILIO_AUTH_TOKEN:
                return "failed", "Twilio credentials are missing."
            twilio_url = (
                f"{SELF_EMPLOYED_TWILIO_API_BASE_URL}/2010-04-01/Accounts/"
                f"{SELF_EMPLOYED_TWILIO_ACCOUNT_SID}/Messages.json"
            )
            form_payload: dict[str, str] = {
                "To": recipient_phone,
                "Body": sms_body,
            }
            if SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID:
                form_payload["MessagingServiceSid"] = SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID
            else:
                form_payload["From"] = SELF_EMPLOYED_REMINDER_SMS_FROM
            await _post_with_delivery_retry(
                twilio_url,
                form_body=form_payload,
                auth=(SELF_EMPLOYED_TWILIO_ACCOUNT_SID, SELF_EMPLOYED_TWILIO_AUTH_TOKEN),
            )
            return "sent", f"SMS reminder sent via Twilio to {recipient_phone}."

        if SELF_EMPLOYED_REMINDER_SMS_PROVIDER == "webhook":
            if not SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL:
                return "failed", "SMS dispatch URL is not configured."
            payload = {
                "provider": "self_employed_invoice_reminders",
                "from": SELF_EMPLOYED_REMINDER_SMS_FROM,
                "to": recipient_phone,
                "message": sms_body,
                "metadata": {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "reminder_type": reminder_type,
                    "dispatch_provider": "webhook",
                },
            }
            await _post_with_delivery_retry(
                SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL,
                json_body=payload,
            )
            return "sent", f"SMS reminder sent to {recipient_phone}."

        return "failed", f"Unsupported SMS provider: {SELF_EMPLOYED_REMINDER_SMS_PROVIDER}"
    except httpx.HTTPError as exc:
        return "failed", _truncate_text(f"SMS dispatch failed: {exc}")


def _build_calendar_reminder_email_subject(
    *,
    title: str,
    reminder_type: Literal["upcoming", "overdue"],
) -> str:
    if reminder_type == "overdue":
        return f"Missed event alert: {title}"
    return f"Upcoming event reminder: {title}"


def _build_calendar_reminder_email_body(
    *,
    title: str,
    starts_at: datetime.datetime,
    reminder_type: Literal["upcoming", "overdue"],
    message: str,
) -> str:
    starts_at_utc = _to_utc_datetime(starts_at)
    headline = (
        f"The event '{title}' is now overdue."
        if reminder_type == "overdue"
        else f"The event '{title}' is coming up soon."
    )
    return "\n".join(
        [
            headline,
            f"Scheduled at (UTC): {starts_at_utc.strftime('%Y-%m-%d %H:%M')}",
            "",
            message,
            "",
            "Sent by SelfMonitor calendar automation.",
        ]
    )


def _build_calendar_reminder_sms_body(
    *,
    title: str,
    starts_at: datetime.datetime,
    reminder_type: Literal["upcoming", "overdue"],
    message: str,
) -> str:
    starts_at_utc = _to_utc_datetime(starts_at)
    prefix = "MISSED EVENT" if reminder_type == "overdue" else "UPCOMING EVENT"
    raw = f"{prefix}: {title} at {starts_at_utc.strftime('%Y-%m-%d %H:%M')} UTC. {message}"
    return _truncate_text(raw, max_length=320)


async def _dispatch_calendar_reminder_email(
    *,
    event_id: str,
    title: str,
    starts_at: datetime.datetime,
    reminder_type: Literal["upcoming", "overdue"],
    message: str,
    recipient_email: str | None,
) -> tuple[Literal["sent", "failed"], str]:
    if not SELF_EMPLOYED_REMINDER_EMAIL_ENABLED:
        return "failed", "Email dispatch disabled by configuration."
    if not recipient_email:
        return "failed", "Recipient email is missing."
    subject = _build_calendar_reminder_email_subject(title=title, reminder_type=reminder_type)
    body = _build_calendar_reminder_email_body(
        title=title,
        starts_at=starts_at,
        reminder_type=reminder_type,
        message=message,
    )

    try:
        if SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER == "sendgrid":
            if not SELF_EMPLOYED_SENDGRID_API_KEY:
                return "failed", "SendGrid API key is missing."
            payload = {
                "personalizations": [{"to": [{"email": recipient_email}]}],
                "from": {"email": SELF_EMPLOYED_REMINDER_EMAIL_FROM},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
                "custom_args": {
                    "calendar_event_id": event_id,
                    "calendar_reminder_type": reminder_type,
                },
            }
            await _post_with_delivery_retry(
                SELF_EMPLOYED_SENDGRID_API_URL,
                headers={
                    "Authorization": f"Bearer {SELF_EMPLOYED_SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json_body=payload,
            )
            return "sent", f"Calendar email reminder sent via SendGrid to {recipient_email}."

        if SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER == "webhook":
            if not SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL:
                return "failed", "Email dispatch URL is not configured."
            payload = {
                "provider": "self_employed_calendar_reminders",
                "from": SELF_EMPLOYED_REMINDER_EMAIL_FROM,
                "to": recipient_email,
                "subject": subject,
                "message": body,
                "metadata": {
                    "event_id": event_id,
                    "event_title": title,
                    "reminder_type": reminder_type,
                    "dispatch_provider": "webhook",
                },
            }
            await _post_with_delivery_retry(
                SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL,
                json_body=payload,
            )
            return "sent", f"Calendar email reminder sent to {recipient_email}."

        return "failed", f"Unsupported email provider: {SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER}"
    except httpx.HTTPError as exc:
        return "failed", _truncate_text(f"Calendar email dispatch failed: {exc}")


async def _dispatch_calendar_reminder_sms(
    *,
    event_id: str,
    title: str,
    starts_at: datetime.datetime,
    reminder_type: Literal["upcoming", "overdue"],
    message: str,
    recipient_phone: str | None,
) -> tuple[Literal["sent", "failed"], str]:
    if not SELF_EMPLOYED_REMINDER_SMS_ENABLED:
        return "failed", "SMS dispatch disabled by configuration."
    if not recipient_phone:
        return "failed", "Recipient phone is missing."
    sms_body = _build_calendar_reminder_sms_body(
        title=title,
        starts_at=starts_at,
        reminder_type=reminder_type,
        message=message,
    )

    try:
        if SELF_EMPLOYED_REMINDER_SMS_PROVIDER == "twilio":
            if not SELF_EMPLOYED_TWILIO_ACCOUNT_SID or not SELF_EMPLOYED_TWILIO_AUTH_TOKEN:
                return "failed", "Twilio credentials are missing."
            twilio_url = (
                f"{SELF_EMPLOYED_TWILIO_API_BASE_URL}/2010-04-01/Accounts/"
                f"{SELF_EMPLOYED_TWILIO_ACCOUNT_SID}/Messages.json"
            )
            form_payload: dict[str, str] = {
                "To": recipient_phone,
                "Body": sms_body,
            }
            if SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID:
                form_payload["MessagingServiceSid"] = SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID
            else:
                form_payload["From"] = SELF_EMPLOYED_REMINDER_SMS_FROM
            await _post_with_delivery_retry(
                twilio_url,
                form_body=form_payload,
                auth=(SELF_EMPLOYED_TWILIO_ACCOUNT_SID, SELF_EMPLOYED_TWILIO_AUTH_TOKEN),
            )
            return "sent", f"Calendar SMS reminder sent via Twilio to {recipient_phone}."

        if SELF_EMPLOYED_REMINDER_SMS_PROVIDER == "webhook":
            if not SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL:
                return "failed", "SMS dispatch URL is not configured."
            payload = {
                "provider": "self_employed_calendar_reminders",
                "from": SELF_EMPLOYED_REMINDER_SMS_FROM,
                "to": recipient_phone,
                "message": sms_body,
                "metadata": {
                    "event_id": event_id,
                    "event_title": title,
                    "reminder_type": reminder_type,
                    "dispatch_provider": "webhook",
                },
            }
            await _post_with_delivery_retry(
                SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL,
                json_body=payload,
            )
            return "sent", f"Calendar SMS reminder sent to {recipient_phone}."

        return "failed", f"Unsupported SMS provider: {SELF_EMPLOYED_REMINDER_SMS_PROVIDER}"
    except httpx.HTTPError as exc:
        return "failed", _truncate_text(f"Calendar SMS dispatch failed: {exc}")


def _email_reminder_config_issues() -> list[str]:
    issues: list[str] = []
    if SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER not in {"webhook", "sendgrid"}:
        issues.append(f"Unsupported email provider: {SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER}")
        return issues
    if SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER == "webhook":
        if not SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL:
            issues.append("SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL is not configured.")
    elif SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER == "sendgrid":
        if not SELF_EMPLOYED_SENDGRID_API_KEY:
            issues.append("SELF_EMPLOYED_SENDGRID_API_KEY is missing.")
        if not SELF_EMPLOYED_SENDGRID_API_URL:
            issues.append("SELF_EMPLOYED_SENDGRID_API_URL is missing.")
    if not SELF_EMPLOYED_REMINDER_EMAIL_FROM:
        issues.append("SELF_EMPLOYED_REMINDER_EMAIL_FROM is not configured.")
    return issues


def _sms_reminder_config_issues() -> list[str]:
    issues: list[str] = []
    if SELF_EMPLOYED_REMINDER_SMS_PROVIDER not in {"webhook", "twilio"}:
        issues.append(f"Unsupported SMS provider: {SELF_EMPLOYED_REMINDER_SMS_PROVIDER}")
        return issues
    if SELF_EMPLOYED_REMINDER_SMS_PROVIDER == "webhook":
        if not SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL:
            issues.append("SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL is not configured.")
    elif SELF_EMPLOYED_REMINDER_SMS_PROVIDER == "twilio":
        if not SELF_EMPLOYED_TWILIO_ACCOUNT_SID:
            issues.append("SELF_EMPLOYED_TWILIO_ACCOUNT_SID is missing.")
        if not SELF_EMPLOYED_TWILIO_AUTH_TOKEN:
            issues.append("SELF_EMPLOYED_TWILIO_AUTH_TOKEN is missing.")
        if not SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID and not SELF_EMPLOYED_REMINDER_SMS_FROM:
            issues.append(
                "Configure SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID or SELF_EMPLOYED_REMINDER_SMS_FROM."
            )
    return issues


def _build_reminder_channel_readiness(
    *,
    channel: Literal["email", "sms"],
) -> schemas.SelfEmployedReminderChannelReadiness:
    if channel == "email":
        provider = SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER
        enabled = SELF_EMPLOYED_REMINDER_EMAIL_ENABLED
        issues = _email_reminder_config_issues()
        checks = [
            f"provider={provider}",
            f"dispatch_timeout_seconds={SELF_EMPLOYED_REMINDER_DISPATCH_TIMEOUT_SECONDS}",
            f"retry_attempts={SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS}",
        ]
    else:
        provider = SELF_EMPLOYED_REMINDER_SMS_PROVIDER
        enabled = SELF_EMPLOYED_REMINDER_SMS_ENABLED
        issues = _sms_reminder_config_issues()
        checks = [
            f"provider={provider}",
            f"dispatch_timeout_seconds={SELF_EMPLOYED_REMINDER_DISPATCH_TIMEOUT_SECONDS}",
            f"retry_attempts={SELF_EMPLOYED_REMINDER_DELIVERY_RETRY_ATTEMPTS}",
        ]

    configured = not issues
    warnings: list[str] = []
    if not enabled:
        warnings.append(f"{channel} channel is disabled.")
    warnings.extend(issues)
    return schemas.SelfEmployedReminderChannelReadiness(
        channel=channel,
        provider=provider,
        enabled=enabled,
        configured=configured,
        can_dispatch=enabled and configured,
        checks=checks,
        warnings=warnings,
    )


def _build_reminder_delivery_readiness_snapshot() -> schemas.SelfEmployedReminderDeliveryReadinessResponse:
    email = _build_reminder_channel_readiness(channel="email")
    sms = _build_reminder_channel_readiness(channel="sms")
    overall_ready = email.can_dispatch or sms.can_dispatch
    note = (
        "At least one delivery channel is ready."
        if overall_ready
        else "No delivery channels are currently ready."
    )
    return schemas.SelfEmployedReminderDeliveryReadinessResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        email=email,
        sms=sms,
        overall_ready=overall_ready,
        note=note,
    )


async def _load_seed_invoice_metrics(
    db: AsyncSession,
    *,
    as_of_date: datetime.date,
    period_months: int,
) -> dict[str, Any]:
    current_month_start = _month_start(as_of_date)
    window_start = _shift_month(current_month_start, -(period_months - 1))
    window_start_at = datetime.datetime.combine(window_start, datetime.time.min, tzinfo=datetime.UTC)

    month_starts = [_shift_month(window_start, offset) for offset in range(period_months)]
    month_totals: dict[str, float] = {_month_key(item): 0.0 for item in month_starts}

    rows = (
        await db.execute(
            select(
                models.BillingInvoice.created_at,
                models.BillingInvoice.total_amount_gbp,
                models.BillingInvoice.status,
            ).filter(
                models.BillingInvoice.created_at >= window_start_at,
                models.BillingInvoice.status != schemas.BillingInvoiceStatus.void.value,
            )
        )
    ).all()

    active_invoice_count = 0
    paid_invoice_count = 0
    for created_at, total_amount_gbp, status_value in rows:
        if not isinstance(created_at, datetime.datetime):
            continue
        created_date = (
            created_at.astimezone(datetime.UTC).date()
            if created_at.tzinfo is not None
            else created_at.date()
        )
        month_key = _month_key(_month_start(created_date))
        if month_key not in month_totals:
            continue
        month_totals[month_key] += float(total_amount_gbp or 0.0)
        active_invoice_count += 1
        if str(status_value) == schemas.BillingInvoiceStatus.paid.value:
            paid_invoice_count += 1

    current_key = _month_key(current_month_start)
    previous_key = _month_key(_shift_month(current_month_start, -1))
    current_month_mrr = round(month_totals.get(current_key, 0.0), 2)
    previous_month_mrr = round(month_totals.get(previous_key, 0.0), 2)
    if previous_month_mrr > 0:
        mrr_growth_percent = round(((current_month_mrr - previous_month_mrr) / previous_month_mrr) * 100, 1)
    elif current_month_mrr > 0:
        mrr_growth_percent = 100.0
    else:
        mrr_growth_percent = 0.0

    rolling_keys = [_month_key(_shift_month(current_month_start, delta)) for delta in (-2, -1, 0)]
    rolling_3_month_avg_mrr = round(sum(month_totals.get(key, 0.0) for key in rolling_keys) / 3.0, 2)
    paid_invoice_rate_percent = (
        round((paid_invoice_count / active_invoice_count) * 100.0, 1)
        if active_invoice_count
        else 0.0
    )
    return {
        "current_month_mrr_gbp": current_month_mrr,
        "previous_month_mrr_gbp": previous_month_mrr,
        "mrr_growth_percent": mrr_growth_percent,
        "rolling_3_month_avg_mrr_gbp": rolling_3_month_avg_mrr,
        "paid_invoice_rate_percent": paid_invoice_rate_percent,
        "active_invoice_count": active_invoice_count,
        "monthly_mrr_series": [
            schemas.SeedMRRPoint(month=_month_key(item), mrr_gbp=round(month_totals[_month_key(item)], 2))
            for item in month_starts
        ],
    }


async def _load_marketing_spend_window(
    db: AsyncSession,
    *,
    window_start: datetime.date,
    window_end: datetime.date,
) -> dict[str, dict[str, float | int]]:
    rows = (
        await db.execute(
            select(
                models.MarketingSpendEntry.month_start,
                models.MarketingSpendEntry.spend_gbp,
                models.MarketingSpendEntry.acquired_customers,
            ).filter(
                models.MarketingSpendEntry.month_start >= window_start,
                models.MarketingSpendEntry.month_start <= window_end,
            )
        )
    ).all()
    bucket: dict[str, dict[str, float | int]] = defaultdict(lambda: {"spend_gbp": 0.0, "acquired_customers": 0})
    for month_start_value, spend_raw, acquired_customers_raw in rows:
        if not isinstance(month_start_value, datetime.date):
            continue
        key = _month_key(_month_start(month_start_value))
        bucket[key]["spend_gbp"] = float(bucket[key]["spend_gbp"]) + float(spend_raw or 0.0)
        bucket[key]["acquired_customers"] = int(bucket[key]["acquired_customers"]) + int(acquired_customers_raw or 0)
    return dict(bucket)


def _mrr_stability_band(stability_percent: float) -> Literal["stable", "variable", "volatile"]:
    if stability_percent >= 85.0:
        return "stable"
    if stability_percent >= 60.0:
        return "variable"
    return "volatile"


async def _build_unit_economics_snapshot(
    db: AsyncSession,
    *,
    period_months: int,
    as_of_date: datetime.date,
) -> schemas.UnitEconomicsResponse:
    invoice_metrics = await _load_seed_invoice_metrics(
        db,
        as_of_date=as_of_date,
        period_months=period_months,
    )
    current_month_start = _month_start(as_of_date)
    window_start = _shift_month(current_month_start, -(period_months - 1))
    month_starts = [_shift_month(window_start, offset) for offset in range(period_months)]

    month_mrr_map: dict[str, float] = {}
    for item in list(invoice_metrics["monthly_mrr_series"]):
        if isinstance(item, schemas.SeedMRRPoint):
            month_mrr_map[item.month] = float(item.mrr_gbp)
        elif isinstance(item, dict):
            month_mrr_map[str(item.get("month"))] = float(item.get("mrr_gbp") or 0.0)

    marketing_spend_by_month = await _load_marketing_spend_window(
        db,
        window_start=window_start,
        window_end=current_month_start,
    )

    monthly_points: list[schemas.UnitEconomicsMonthlyPoint] = []
    churn_rates: list[float] = []
    expansion_rates: list[float] = []
    mrr_values: list[float] = []
    for index, month_start in enumerate(month_starts):
        month_key = _month_key(month_start)
        mrr_value = round(float(month_mrr_map.get(month_key, 0.0)), 2)
        mrr_values.append(mrr_value)
        previous_month_mrr = 0.0
        churn_rate_percent = 0.0
        expansion_rate_percent = 0.0
        if index > 0:
            previous_key = _month_key(month_starts[index - 1])
            previous_month_mrr = round(float(month_mrr_map.get(previous_key, 0.0)), 2)
            if previous_month_mrr > 0:
                churn_rate_percent = round((max(previous_month_mrr - mrr_value, 0.0) / previous_month_mrr) * 100.0, 1)
                expansion_rate_percent = round((max(mrr_value - previous_month_mrr, 0.0) / previous_month_mrr) * 100.0, 1)
                churn_rates.append(churn_rate_percent)
                expansion_rates.append(expansion_rate_percent)
        spend_row = marketing_spend_by_month.get(month_key, {})
        spend_gbp = round(float(spend_row.get("spend_gbp") or 0.0), 2)
        acquired_customers = int(spend_row.get("acquired_customers") or 0)
        cac_gbp = round(spend_gbp / acquired_customers, 2) if acquired_customers > 0 else None
        monthly_points.append(
            schemas.UnitEconomicsMonthlyPoint(
                month=month_key,
                mrr_gbp=mrr_value,
                previous_month_mrr_gbp=previous_month_mrr,
                churn_rate_percent=churn_rate_percent,
                expansion_rate_percent=expansion_rate_percent,
                marketing_spend_gbp=spend_gbp,
                acquired_customers=acquired_customers,
                cac_gbp=cac_gbp,
            )
        )

    monthly_churn_rate_percent = round(sum(churn_rates) / len(churn_rates), 1) if churn_rates else 0.0
    monthly_expansion_rate_percent = round(sum(expansion_rates) / len(expansion_rates), 1) if expansion_rates else 0.0

    mean_mrr = (sum(mrr_values) / len(mrr_values)) if mrr_values else 0.0
    if len(mrr_values) >= 2 and mean_mrr > 0:
        variance = sum((item - mean_mrr) ** 2 for item in mrr_values) / len(mrr_values)
        coefficient_variation = math.sqrt(variance) / mean_mrr
        mrr_stability_percent = round(max(0.0, min(100.0, 100.0 - (coefficient_variation * 100.0))), 1)
    elif mean_mrr > 0:
        mrr_stability_percent = 100.0
    else:
        mrr_stability_percent = 0.0
    mrr_stability_band = _mrr_stability_band(mrr_stability_percent)

    total_marketing_spend = round(sum(float(item.get("spend_gbp") or 0.0) for item in marketing_spend_by_month.values()), 2)
    total_acquired_customers = sum(int(item.get("acquired_customers") or 0) for item in marketing_spend_by_month.values())
    average_cac_gbp = (
        round(total_marketing_spend / total_acquired_customers, 2) if total_acquired_customers > 0 else None
    )

    estimated_ltv_gbp: float | None = None
    ltv_cac_ratio: float | None = None
    if total_acquired_customers > 0 and mean_mrr > 0:
        avg_new_customers_per_month = total_acquired_customers / max(period_months, 1)
        proxy_monthly_arpu = mean_mrr / max(avg_new_customers_per_month, 1e-6)
        churn_fraction = monthly_churn_rate_percent / 100.0
        if churn_fraction > 0:
            expected_lifetime_months = min(60.0, max(1.0, 1.0 / churn_fraction))
        else:
            expected_lifetime_months = 24.0
        estimated_ltv_gbp = round(proxy_monthly_arpu * expected_lifetime_months, 2)
        if average_cac_gbp and average_cac_gbp > 0:
            ltv_cac_ratio = round(estimated_ltv_gbp / average_cac_gbp, 2)

    current_month_mrr = float(invoice_metrics["current_month_mrr_gbp"])
    mrr_gate_passed = current_month_mrr >= SEED_GATE_REQUIRED_MRR_GBP
    churn_gate_passed = monthly_churn_rate_percent < SEED_GATE_MAX_MONTHLY_CHURN_PERCENT
    ltv_cac_gate_passed = bool(ltv_cac_ratio is not None and ltv_cac_ratio >= SEED_GATE_MIN_LTV_CAC_RATIO)
    seed_gate_passed = mrr_gate_passed and churn_gate_passed and ltv_cac_gate_passed

    next_actions: list[str] = []
    if total_acquired_customers == 0:
        next_actions.append("Ingest monthly marketing spend and acquired-customer counts to unlock CAC/LTV tracking.")
    if not mrr_gate_passed:
        next_actions.append("Increase monthly recurring revenue above the seed gate target with conversion and pricing actions.")
    if not churn_gate_passed:
        next_actions.append("Reduce monthly churn below threshold with retention and lifecycle intervention workflows.")
    if not ltv_cac_gate_passed:
        next_actions.append("Improve LTV/CAC ratio through channel quality optimization and onboarding efficiency gains.")
    if not next_actions:
        next_actions.append("Seed gate is currently passing; maintain cadence and monitor variance weekly.")

    return schemas.UnitEconomicsResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        as_of_date=as_of_date,
        period_months=period_months,
        current_month_mrr_gbp=current_month_mrr,
        rolling_3_month_avg_mrr_gbp=float(invoice_metrics["rolling_3_month_avg_mrr_gbp"]),
        mrr_growth_percent=float(invoice_metrics["mrr_growth_percent"]),
        mrr_stability_percent=mrr_stability_percent,
        mrr_stability_band=mrr_stability_band,
        monthly_churn_rate_percent=monthly_churn_rate_percent,
        monthly_expansion_rate_percent=monthly_expansion_rate_percent,
        average_cac_gbp=average_cac_gbp,
        estimated_ltv_gbp=estimated_ltv_gbp,
        ltv_cac_ratio=ltv_cac_ratio,
        required_mrr_gbp=SEED_GATE_REQUIRED_MRR_GBP,
        required_max_monthly_churn_percent=SEED_GATE_MAX_MONTHLY_CHURN_PERCENT,
        required_min_ltv_cac_ratio=SEED_GATE_MIN_LTV_CAC_RATIO,
        mrr_gate_passed=mrr_gate_passed,
        churn_gate_passed=churn_gate_passed,
        ltv_cac_gate_passed=ltv_cac_gate_passed,
        seed_gate_passed=seed_gate_passed,
        next_actions=next_actions,
        monthly_points=monthly_points,
    )


def _build_seed_readiness_assessment(
    *,
    leads_last_90d: int,
    conversion_rate_percent: float,
    mrr_growth_percent: float,
    paid_invoice_rate_percent: float,
) -> tuple[float, Literal["early", "progressing", "investable"], list[str]]:
    score = 0.0
    if leads_last_90d >= 20:
        score += 25.0
    elif leads_last_90d >= 10:
        score += 15.0
    elif leads_last_90d > 0:
        score += 8.0

    if conversion_rate_percent >= 20.0:
        score += 25.0
    elif conversion_rate_percent >= 10.0:
        score += 15.0
    elif conversion_rate_percent >= 5.0:
        score += 8.0

    if mrr_growth_percent >= 12.0:
        score += 25.0
    elif mrr_growth_percent >= 0.0:
        score += 15.0
    elif mrr_growth_percent > -10.0:
        score += 8.0

    if paid_invoice_rate_percent >= 80.0:
        score += 25.0
    elif paid_invoice_rate_percent >= 60.0:
        score += 15.0
    elif paid_invoice_rate_percent >= 40.0:
        score += 8.0

    if score >= 80.0:
        readiness_band: Literal["early", "progressing", "investable"] = "investable"
    elif score >= 55.0:
        readiness_band = "progressing"
    else:
        readiness_band = "early"

    next_actions: list[str] = []
    if leads_last_90d < 20:
        next_actions.append("Increase top-of-funnel lead volume and onboarding completion in the next 30 days.")
    if conversion_rate_percent < 20.0:
        next_actions.append("Improve conversion from qualified to converted leads via assisted handoff workflows.")
    if mrr_growth_percent < 12.0:
        next_actions.append("Improve MRR momentum with pricing and partner channel experiments.")
    if paid_invoice_rate_percent < 80.0:
        next_actions.append("Increase collection efficiency and reduce outstanding invoice aging.")
    if not next_actions:
        next_actions.append("Maintain current trajectory and prepare investor data-room evidence exports.")

    return round(score, 1), readiness_band, next_actions


async def _build_seed_readiness_snapshot(
    db: AsyncSession,
    *,
    period_months: int,
    as_of_date: datetime.date,
) -> schemas.SeedReadinessResponse:
    invoice_metrics = await _load_seed_invoice_metrics(
        db,
        as_of_date=as_of_date,
        period_months=period_months,
    )
    start_date_90d = as_of_date - datetime.timedelta(days=89)
    funnel_report = await _load_billing_report(
        db=db,
        partner_id=None,
        start_date=start_date_90d,
        end_date=as_of_date,
        statuses=[],
    )
    leads_last_90d = funnel_report.total_leads
    qualified_last_90d = funnel_report.qualified_leads
    converted_last_90d = funnel_report.converted_leads
    qualification_rate_percent = (
        round((qualified_last_90d / leads_last_90d) * 100.0, 1) if leads_last_90d else 0.0
    )
    conversion_rate_percent = (
        round((converted_last_90d / leads_last_90d) * 100.0, 1) if leads_last_90d else 0.0
    )
    readiness_score_percent, readiness_band, next_actions = _build_seed_readiness_assessment(
        leads_last_90d=leads_last_90d,
        conversion_rate_percent=conversion_rate_percent,
        mrr_growth_percent=float(invoice_metrics["mrr_growth_percent"]),
        paid_invoice_rate_percent=float(invoice_metrics["paid_invoice_rate_percent"]),
    )
    return schemas.SeedReadinessResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        period_months=period_months,
        current_month_mrr_gbp=float(invoice_metrics["current_month_mrr_gbp"]),
        previous_month_mrr_gbp=float(invoice_metrics["previous_month_mrr_gbp"]),
        mrr_growth_percent=float(invoice_metrics["mrr_growth_percent"]),
        rolling_3_month_avg_mrr_gbp=float(invoice_metrics["rolling_3_month_avg_mrr_gbp"]),
        paid_invoice_rate_percent=float(invoice_metrics["paid_invoice_rate_percent"]),
        active_invoice_count=int(invoice_metrics["active_invoice_count"]),
        leads_last_90d=leads_last_90d,
        qualified_last_90d=qualified_last_90d,
        converted_last_90d=converted_last_90d,
        qualification_rate_percent=qualification_rate_percent,
        conversion_rate_percent=conversion_rate_percent,
        readiness_score_percent=readiness_score_percent,
        readiness_band=readiness_band,
        next_actions=next_actions,
        monthly_mrr_series=list(invoice_metrics["monthly_mrr_series"]),
    )


def _to_utc_date(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(datetime.UTC).date()
    if isinstance(value, datetime.date):
        return value
    return None


def _retained_in_window(
    *,
    first_seen: datetime.date,
    activity_dates: set[datetime.date],
    start_day: int,
) -> bool:
    window_start = first_seen + datetime.timedelta(days=start_day)
    window_end = window_start + datetime.timedelta(days=29)
    return any(window_start <= activity_date <= window_end for activity_date in activity_dates)


async def _load_pmf_user_activity(
    db: AsyncSession,
    *,
    cohort_start: datetime.date,
    as_of_date: datetime.date,
) -> dict[str, dict[str, Any]]:
    first_seen_rows = (
        await db.execute(
            select(
                models.HandoffLead.user_id,
                func.min(models.HandoffLead.created_at).label("first_seen_at"),
            ).group_by(models.HandoffLead.user_id)
        )
    ).all()

    first_seen_by_user: dict[str, datetime.date] = {}
    for user_id_value, first_seen_at in first_seen_rows:
        first_seen_date = _to_utc_date(first_seen_at)
        if not first_seen_date:
            continue
        if cohort_start <= first_seen_date <= as_of_date:
            first_seen_by_user[str(user_id_value)] = first_seen_date

    if not first_seen_by_user:
        return {}

    activity_rows = (
        await db.execute(
            select(
                models.HandoffLead.user_id,
                models.HandoffLead.created_at,
                models.HandoffLead.updated_at,
                models.HandoffLead.status,
            ).filter(models.HandoffLead.user_id.in_(list(first_seen_by_user.keys())))
        )
    ).all()

    activity_by_user: dict[str, dict[str, Any]] = {
        user_id: {
            "first_seen": first_seen_date,
            "activity_dates": set(),
            "activation_dates": set(),
        }
        for user_id, first_seen_date in first_seen_by_user.items()
    }
    activation_statuses = {
        schemas.LeadStatus.qualified.value,
        schemas.LeadStatus.converted.value,
    }
    for user_id_value, created_at, updated_at, status_value in activity_rows:
        user_id = str(user_id_value)
        row = activity_by_user.get(user_id)
        if row is None:
            continue
        created_date = _to_utc_date(created_at)
        updated_date = _to_utc_date(updated_at)
        if created_date:
            row["activity_dates"].add(created_date)
        if updated_date:
            row["activity_dates"].add(updated_date)
        if str(status_value) in activation_statuses:
            activation_date = updated_date or created_date
            if activation_date:
                row["activation_dates"].add(activation_date)
    return activity_by_user


def _build_user_pmf_flags(
    *,
    activity_by_user: dict[str, dict[str, Any]],
    as_of_date: datetime.date,
    activation_window_days: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for user_id, row in activity_by_user.items():
        first_seen = row["first_seen"]
        if not isinstance(first_seen, datetime.date):
            continue
        activity_dates_raw = row["activity_dates"]
        activation_dates_raw = row["activation_dates"]
        activity_dates = activity_dates_raw if isinstance(activity_dates_raw, set) else set()
        activation_dates = activation_dates_raw if isinstance(activation_dates_raw, set) else set()
        activation_deadline = first_seen + datetime.timedelta(days=activation_window_days)
        activated = any(first_seen <= activation_date <= activation_deadline for activation_date in activation_dates)
        eligible_30 = as_of_date >= first_seen + datetime.timedelta(days=30)
        eligible_60 = as_of_date >= first_seen + datetime.timedelta(days=60)
        eligible_90 = as_of_date >= first_seen + datetime.timedelta(days=90)
        rows.append(
            {
                "user_id": user_id,
                "first_seen": first_seen,
                "activated": activated,
                "eligible_30": eligible_30,
                "eligible_60": eligible_60,
                "eligible_90": eligible_90,
                "retained_30": eligible_30 and _retained_in_window(first_seen=first_seen, activity_dates=activity_dates, start_day=30),
                "retained_60": eligible_60 and _retained_in_window(first_seen=first_seen, activity_dates=activity_dates, start_day=60),
                "retained_90": eligible_90 and _retained_in_window(first_seen=first_seen, activity_dates=activity_dates, start_day=90),
            }
        )
    return rows


def _aggregate_pmf_flags(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    total_new_users = len(rows)
    activated_users = sum(1 for row in rows if bool(row.get("activated")))
    eligible_users_30d = sum(1 for row in rows if bool(row.get("eligible_30")))
    eligible_users_60d = sum(1 for row in rows if bool(row.get("eligible_60")))
    eligible_users_90d = sum(1 for row in rows if bool(row.get("eligible_90")))
    retained_users_30d = sum(1 for row in rows if bool(row.get("retained_30")))
    retained_users_60d = sum(1 for row in rows if bool(row.get("retained_60")))
    retained_users_90d = sum(1 for row in rows if bool(row.get("retained_90")))
    return {
        "total_new_users": total_new_users,
        "activated_users": activated_users,
        "activation_rate_percent": round((activated_users / total_new_users) * 100.0, 1) if total_new_users else 0.0,
        "eligible_users_30d": eligible_users_30d,
        "retained_users_30d": retained_users_30d,
        "retention_rate_30d_percent": (
            round((retained_users_30d / eligible_users_30d) * 100.0, 1) if eligible_users_30d else 0.0
        ),
        "eligible_users_60d": eligible_users_60d,
        "retained_users_60d": retained_users_60d,
        "retention_rate_60d_percent": (
            round((retained_users_60d / eligible_users_60d) * 100.0, 1) if eligible_users_60d else 0.0
        ),
        "eligible_users_90d": eligible_users_90d,
        "retained_users_90d": retained_users_90d,
        "retention_rate_90d_percent": (
            round((retained_users_90d / eligible_users_90d) * 100.0, 1) if eligible_users_90d else 0.0
        ),
    }


def _assess_pmf_band(
    *,
    total_new_users: int,
    activation_rate_percent: float,
    retention_rate_30d_percent: float,
    retention_rate_90d_percent: float,
) -> tuple[Literal["early", "emerging", "pmf_confirmed"], list[str]]:
    if total_new_users >= 25 and activation_rate_percent >= 60.0 and retention_rate_90d_percent >= 75.0:
        band: Literal["early", "emerging", "pmf_confirmed"] = "pmf_confirmed"
    elif total_new_users >= 8 and activation_rate_percent >= 45.0 and retention_rate_30d_percent >= 35.0:
        band = "emerging"
    else:
        band = "early"

    notes: list[str] = [
        "Retention cohorts are based on user activity in handoff lifecycle events (created/updated).",
        "Activation is measured as reaching qualified/converted status within the activation window.",
    ]
    if band == "pmf_confirmed":
        notes.append("PMF thresholds met for current cohort sample and retention windows.")
    elif band == "emerging":
        notes.append("Signals are improving; continue increasing cohort size and 90-day retention quality.")
    else:
        notes.append("Early-stage PMF signal; focus on onboarding quality and consistent return usage.")
    return band, notes


async def _build_pmf_evidence_snapshot(
    db: AsyncSession,
    *,
    cohort_months: int,
    activation_window_days: int,
    as_of_date: datetime.date,
) -> schemas.PMFEvidenceResponse:
    cohort_start = _shift_month(_month_start(as_of_date), -(cohort_months - 1))
    activity_by_user = await _load_pmf_user_activity(
        db,
        cohort_start=cohort_start,
        as_of_date=as_of_date,
    )
    pmf_rows = _build_user_pmf_flags(
        activity_by_user=activity_by_user,
        as_of_date=as_of_date,
        activation_window_days=activation_window_days,
    )
    overall = _aggregate_pmf_flags(pmf_rows)
    pmf_band, notes = _assess_pmf_band(
        total_new_users=int(overall["total_new_users"]),
        activation_rate_percent=float(overall["activation_rate_percent"]),
        retention_rate_30d_percent=float(overall["retention_rate_30d_percent"]),
        retention_rate_90d_percent=float(overall["retention_rate_90d_percent"]),
    )

    cohort_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pmf_rows:
        first_seen = row.get("first_seen")
        if isinstance(first_seen, datetime.date):
            cohort_bucket[_month_key(_month_start(first_seen))].append(row)

    month_starts = [_shift_month(cohort_start, offset) for offset in range(cohort_months)]
    monthly_cohorts: list[schemas.PMFMonthlyCohortPoint] = []
    for month_start in month_starts:
        month_key = _month_key(month_start)
        cohort_rows = cohort_bucket.get(month_key, [])
        month_agg = _aggregate_pmf_flags(cohort_rows)
        monthly_cohorts.append(
            schemas.PMFMonthlyCohortPoint(
                cohort_month=month_key,
                new_users=int(month_agg["total_new_users"]),
                activated_users=int(month_agg["activated_users"]),
                activation_rate_percent=float(month_agg["activation_rate_percent"]),
                eligible_users_30d=int(month_agg["eligible_users_30d"]),
                retained_users_30d=int(month_agg["retained_users_30d"]),
                retention_rate_30d_percent=float(month_agg["retention_rate_30d_percent"]),
                eligible_users_60d=int(month_agg["eligible_users_60d"]),
                retained_users_60d=int(month_agg["retained_users_60d"]),
                retention_rate_60d_percent=float(month_agg["retention_rate_60d_percent"]),
                eligible_users_90d=int(month_agg["eligible_users_90d"]),
                retained_users_90d=int(month_agg["retained_users_90d"]),
                retention_rate_90d_percent=float(month_agg["retention_rate_90d_percent"]),
            )
        )

    return schemas.PMFEvidenceResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        as_of_date=as_of_date,
        cohort_months=cohort_months,
        activation_window_days=activation_window_days,
        total_new_users=int(overall["total_new_users"]),
        activated_users=int(overall["activated_users"]),
        activation_rate_percent=float(overall["activation_rate_percent"]),
        eligible_users_30d=int(overall["eligible_users_30d"]),
        retained_users_30d=int(overall["retained_users_30d"]),
        retention_rate_30d_percent=float(overall["retention_rate_30d_percent"]),
        eligible_users_60d=int(overall["eligible_users_60d"]),
        retained_users_60d=int(overall["retained_users_60d"]),
        retention_rate_60d_percent=float(overall["retention_rate_60d_percent"]),
        eligible_users_90d=int(overall["eligible_users_90d"]),
        retained_users_90d=int(overall["retained_users_90d"]),
        retention_rate_90d_percent=float(overall["retention_rate_90d_percent"]),
        pmf_band=pmf_band,
        notes=notes,
        monthly_cohorts=monthly_cohorts,
    )


def _build_pmf_gate_status(
    *,
    pmf_evidence: schemas.PMFEvidenceResponse,
    nps_trend: schemas.NPSTrendResponse,
) -> schemas.PMFGateStatusResponse:
    activation_passed = pmf_evidence.activation_rate_percent >= PMF_GATE_REQUIRED_ACTIVATION_RATE_PERCENT
    retention_passed = pmf_evidence.retention_rate_90d_percent >= PMF_GATE_REQUIRED_RETENTION_90D_PERCENT
    nps_passed = nps_trend.overall_nps_score >= PMF_GATE_REQUIRED_NPS_SCORE
    sample_size_passed = (
        pmf_evidence.eligible_users_90d >= PMF_GATE_MIN_ELIGIBLE_USERS_90D
        and nps_trend.total_responses >= PMF_GATE_MIN_NPS_RESPONSES
    )
    gate_passed = activation_passed and retention_passed and nps_passed and sample_size_passed
    if gate_passed:
        summary = "PMF gate passed: activation, long-term retention, and NPS all meet target thresholds."
    else:
        summary = "PMF gate not yet passed: one or more threshold checks remain below target."

    next_actions: list[str] = []
    if not activation_passed:
        next_actions.append("Increase activation quality to reach or exceed the configured threshold.")
    if not retention_passed:
        next_actions.append("Improve 90-day retention through recurring value loops and reminder nudges.")
    if not nps_passed:
        next_actions.append("Raise NPS by addressing top detractor themes and shortening support response loops.")
    if not sample_size_passed:
        next_actions.append("Increase cohort/NPS sample size to improve confidence in PMF decisioning.")
    if not next_actions:
        next_actions.append("Maintain PMF performance and keep monitoring thresholds weekly.")

    return schemas.PMFGateStatusResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        gate_name="seed_pmf_gate_v1",
        activation_rate_percent=pmf_evidence.activation_rate_percent,
        retention_rate_90d_percent=pmf_evidence.retention_rate_90d_percent,
        overall_nps_score=nps_trend.overall_nps_score,
        eligible_users_90d=pmf_evidence.eligible_users_90d,
        total_nps_responses=nps_trend.total_responses,
        required_activation_rate_percent=PMF_GATE_REQUIRED_ACTIVATION_RATE_PERCENT,
        required_retention_rate_90d_percent=PMF_GATE_REQUIRED_RETENTION_90D_PERCENT,
        required_overall_nps_score=PMF_GATE_REQUIRED_NPS_SCORE,
        required_min_eligible_users_90d=PMF_GATE_MIN_ELIGIBLE_USERS_90D,
        required_min_nps_responses=PMF_GATE_MIN_NPS_RESPONSES,
        activation_passed=activation_passed,
        retention_passed=retention_passed,
        nps_passed=nps_passed,
        sample_size_passed=sample_size_passed,
        gate_passed=gate_passed,
        summary=summary,
        next_actions=next_actions,
    )


def _nps_score_band(score: int) -> Literal["promoter", "passive", "detractor"]:
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def _nps_score_from_counts(*, promoters: int, detractors: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(((promoters - detractors) / total) * 100.0, 1)


async def _load_nps_trend(
    db: AsyncSession,
    *,
    as_of_date: datetime.date,
    period_months: int,
) -> dict[str, Any]:
    period_start = _shift_month(_month_start(as_of_date), -(period_months - 1))
    period_start_at = datetime.datetime.combine(period_start, datetime.time.min, tzinfo=datetime.UTC)
    period_end_before = datetime.datetime.combine(
        as_of_date + datetime.timedelta(days=1),
        datetime.time.min,
        tzinfo=datetime.UTC,
    )

    month_starts = [_shift_month(period_start, offset) for offset in range(period_months)]
    bucket: dict[str, dict[str, int]] = {
        _month_key(month_start): {
            "responses_count": 0,
            "promoters_count": 0,
            "passives_count": 0,
            "detractors_count": 0,
        }
        for month_start in month_starts
    }

    rows = (
        await db.execute(
            select(
                models.NPSResponse.created_at,
                models.NPSResponse.score,
            ).filter(
                models.NPSResponse.created_at >= period_start_at,
                models.NPSResponse.created_at < period_end_before,
            )
        )
    ).all()

    for created_at, score_raw in rows:
        created_date = _to_utc_date(created_at)
        if created_date is None:
            continue
        month_key = _month_key(_month_start(created_date))
        month_row = bucket.get(month_key)
        if month_row is None:
            continue
        score = int(score_raw)
        month_row["responses_count"] += 1
        score_band = _nps_score_band(score)
        if score_band == "promoter":
            month_row["promoters_count"] += 1
        elif score_band == "passive":
            month_row["passives_count"] += 1
        else:
            month_row["detractors_count"] += 1

    monthly_trend: list[schemas.NPSMonthlyTrendPoint] = []
    total_responses = 0
    promoters_count = 0
    passives_count = 0
    detractors_count = 0
    for month_start in month_starts:
        key = _month_key(month_start)
        item = bucket[key]
        responses_count = int(item["responses_count"])
        month_promoters = int(item["promoters_count"])
        month_passives = int(item["passives_count"])
        month_detractors = int(item["detractors_count"])
        total_responses += responses_count
        promoters_count += month_promoters
        passives_count += month_passives
        detractors_count += month_detractors
        monthly_trend.append(
            schemas.NPSMonthlyTrendPoint(
                month=key,
                responses_count=responses_count,
                promoters_count=month_promoters,
                passives_count=month_passives,
                detractors_count=month_detractors,
                nps_score=_nps_score_from_counts(
                    promoters=month_promoters,
                    detractors=month_detractors,
                    total=responses_count,
                ),
            )
        )

    return {
        "period_months": period_months,
        "total_responses": total_responses,
        "promoters_count": promoters_count,
        "passives_count": passives_count,
        "detractors_count": detractors_count,
        "overall_nps_score": _nps_score_from_counts(
            promoters=promoters_count,
            detractors=detractors_count,
            total=total_responses,
        ),
        "monthly_trend": monthly_trend,
    }


def _build_nps_trend_response(
    *,
    period_months: int,
    trend: dict[str, Any],
) -> schemas.NPSTrendResponse:
    return schemas.NPSTrendResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        period_months=period_months,
        total_responses=int(trend["total_responses"]),
        promoters_count=int(trend["promoters_count"]),
        passives_count=int(trend["passives_count"]),
        detractors_count=int(trend["detractors_count"]),
        overall_nps_score=float(trend["overall_nps_score"]),
        monthly_trend=list(trend["monthly_trend"]),
        note=(
            "NPS score is calculated as %promoters (9-10) minus %detractors (0-6). "
            "Passives (7-8) are included in response count but not in score numerator."
        ),
    )


def _build_investor_snapshot_csv(snapshot: schemas.InvestorSnapshotExportResponse) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "metric", "value"])
    writer.writerow(["meta", "generated_at", snapshot.generated_at.isoformat()])
    writer.writerow(["meta", "as_of_date", snapshot.as_of_date.isoformat()])

    writer.writerow(["seed_readiness", "readiness_score_percent", f"{snapshot.seed_readiness.readiness_score_percent:.1f}"])
    writer.writerow(["seed_readiness", "readiness_band", snapshot.seed_readiness.readiness_band])
    writer.writerow(["seed_readiness", "mrr_growth_percent", f"{snapshot.seed_readiness.mrr_growth_percent:.1f}"])
    writer.writerow(
        ["seed_readiness", "paid_invoice_rate_percent", f"{snapshot.seed_readiness.paid_invoice_rate_percent:.1f}"]
    )

    writer.writerow(["pmf", "activation_rate_percent", f"{snapshot.pmf_evidence.activation_rate_percent:.1f}"])
    writer.writerow(["pmf", "retention_rate_90d_percent", f"{snapshot.pmf_evidence.retention_rate_90d_percent:.1f}"])
    writer.writerow(["pmf", "pmf_band", snapshot.pmf_evidence.pmf_band])

    writer.writerow(["nps", "overall_nps_score", f"{snapshot.nps_trend.overall_nps_score:.1f}"])
    writer.writerow(["nps", "total_responses", snapshot.nps_trend.total_responses])

    writer.writerow(["pmf_gate", "gate_passed", str(snapshot.pmf_gate.gate_passed).lower()])
    writer.writerow(["pmf_gate", "summary", snapshot.pmf_gate.summary])
    for index, action in enumerate(snapshot.pmf_gate.next_actions, start=1):
        writer.writerow(["pmf_gate_next_action", f"item_{index}", action])

    writer.writerow(["unit_economics", "seed_gate_passed", str(snapshot.unit_economics.seed_gate_passed).lower()])
    writer.writerow(["unit_economics", "current_month_mrr_gbp", f"{snapshot.unit_economics.current_month_mrr_gbp:.2f}"])
    writer.writerow(
        ["unit_economics", "monthly_churn_rate_percent", f"{snapshot.unit_economics.monthly_churn_rate_percent:.1f}"]
    )
    writer.writerow(
        ["unit_economics", "ltv_cac_ratio", "" if snapshot.unit_economics.ltv_cac_ratio is None else snapshot.unit_economics.ltv_cac_ratio]
    )

    return output.getvalue()


def _resolve_report_statuses(
    billable_only: bool,
    statuses: list[schemas.LeadStatus] | None,
) -> list[str] | None:
    if statuses:
        return [status_item.value for status_item in statuses]
    if billable_only:
        return list(DEFAULT_BILLABLE_STATUSES)
    return None


def _resolve_billing_statuses(statuses: list[schemas.LeadStatus] | None) -> list[str]:
    if not statuses:
        return list(DEFAULT_BILLING_STATUSES)

    status_values = [status_item.value for status_item in statuses]
    invalid = [status for status in status_values if status not in DEFAULT_BILLING_STATUSES]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Billing report supports only qualified/converted statuses; "
                f"invalid values: {', '.join(invalid)}"
            ),
        )
    return status_values


def _validate_status_transition(current_status: str, target_status: schemas.LeadStatus) -> None:
    if target_status.value == current_status:
        return

    allowed = LEAD_STATUS_TRANSITIONS.get(current_status, set())
    if target_status.value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition lead status from {current_status} to {target_status.value}",
        )


def _validate_invoice_status_transition(
    current_status: str,
    target_status: schemas.BillingInvoiceStatus,
) -> None:
    if target_status.value == current_status:
        return

    allowed = INVOICE_STATUS_TRANSITIONS.get(current_status, set())
    if target_status.value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition invoice status from {current_status} to {target_status.value}",
        )


def _validate_self_employed_invoice_status_transition(
    current_status: str,
    target_status: schemas.SelfEmployedInvoiceStatus,
) -> None:
    if target_status.value == current_status:
        return

    allowed = SELF_EMPLOYED_INVOICE_STATUS_TRANSITIONS.get(current_status, set())
    if target_status.value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot transition self-employed invoice status "
                f"from {current_status} to {target_status.value}"
            ),
        )


def _to_invoice_summary(invoice: Any) -> schemas.BillingInvoiceSummary:
    return schemas.BillingInvoiceSummary(
        id=uuid.UUID(str(invoice.id)),
        invoice_number=str(invoice.invoice_number),
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        due_date=invoice.due_date,
        currency=invoice.currency,
        status=schemas.BillingInvoiceStatus(invoice.status),
        total_amount_gbp=invoice.total_amount_gbp,
        created_at=invoice.created_at,
    )


def _to_self_employed_invoice_summary(invoice: Any) -> schemas.SelfEmployedInvoiceSummary:
    return schemas.SelfEmployedInvoiceSummary(
        id=uuid.UUID(str(invoice.id)),
        invoice_number=str(invoice.invoice_number),
        customer_name=str(invoice.customer_name),
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        payment_link_url=invoice.payment_link_url,
        status=schemas.SelfEmployedInvoiceStatus(invoice.status),
        total_amount_gbp=invoice.total_amount_gbp,
        created_at=invoice.created_at,
    )


async def _load_invoice_detail(
    db: AsyncSession,
    invoice_id: uuid.UUID,
) -> schemas.BillingInvoiceDetail:
    invoice = await crud.get_billing_invoice_by_id(db, str(invoice_id))
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    lines = await crud.get_billing_invoice_lines(db, str(invoice.id))
    return schemas.BillingInvoiceDetail(
        id=uuid.UUID(str(invoice.id)),
        invoice_number=str(invoice.invoice_number),
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        due_date=invoice.due_date,
        currency=invoice.currency,
        status=schemas.BillingInvoiceStatus(invoice.status),
        total_amount_gbp=invoice.total_amount_gbp,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        generated_by_user_id=invoice.generated_by_user_id,
        partner_id=uuid.UUID(str(invoice.partner_id)) if invoice.partner_id else None,
        statuses=[schemas.LeadStatus(status_value) for status_value in (invoice.statuses or [])],
        lines=[
            schemas.BillingInvoiceLine(
                partner_id=uuid.UUID(str(line.partner_id)),
                partner_name=line.partner_name,
                qualified_leads=line.qualified_leads,
                converted_leads=line.converted_leads,
                unique_users=line.unique_users,
                qualified_lead_fee_gbp=line.qualified_lead_fee_gbp,
                converted_lead_fee_gbp=line.converted_lead_fee_gbp,
                amount_gbp=line.amount_gbp,
            )
            for line in lines
        ],
    )


async def _load_self_employed_invoice_detail(
    db: AsyncSession,
    *,
    invoice_id: uuid.UUID,
    user_id: str,
) -> schemas.SelfEmployedInvoiceDetail:
    invoice = await crud.get_self_employed_invoice_by_id_for_user(
        db,
        invoice_id=str(invoice_id),
        user_id=user_id,
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Self-employed invoice not found")
    lines = await crud.get_self_employed_invoice_lines(db, invoice_id=str(invoice.id))
    return schemas.SelfEmployedInvoiceDetail(
        id=uuid.UUID(str(invoice.id)),
        invoice_number=str(invoice.invoice_number),
        customer_name=str(invoice.customer_name),
        customer_email=invoice.customer_email,
        customer_phone=invoice.customer_phone,
        customer_address=invoice.customer_address,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        payment_link_url=invoice.payment_link_url,
        payment_link_provider=invoice.payment_link_provider,
        status=schemas.SelfEmployedInvoiceStatus(invoice.status),
        subtotal_gbp=invoice.subtotal_gbp,
        tax_rate_percent=invoice.tax_rate_percent,
        tax_amount_gbp=invoice.tax_amount_gbp,
        total_amount_gbp=invoice.total_amount_gbp,
        recurring_plan_id=uuid.UUID(str(invoice.recurring_plan_id)) if invoice.recurring_plan_id else None,
        brand_business_name=invoice.brand_business_name,
        brand_logo_url=invoice.brand_logo_url,
        brand_accent_color=invoice.brand_accent_color,
        reminder_last_sent_at=invoice.reminder_last_sent_at,
        notes=invoice.notes,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        lines=[
            schemas.SelfEmployedInvoiceLine(
                id=uuid.UUID(str(item.id)),
                description=str(item.description),
                quantity=float(item.quantity),
                unit_price_gbp=float(item.unit_price_gbp),
                line_total_gbp=float(item.line_total_gbp),
            )
            for item in lines
        ],
    )


def _to_recurring_plan_summary(plan: Any) -> schemas.SelfEmployedRecurringInvoicePlanSummary:
    return schemas.SelfEmployedRecurringInvoicePlanSummary(
        id=uuid.UUID(str(plan.id)),
        customer_name=str(plan.customer_name),
        cadence=schemas.SelfEmployedRecurringCadence(plan.cadence),
        next_issue_date=plan.next_issue_date,
        active=bool(plan.active),
        last_generated_invoice_id=uuid.UUID(str(plan.last_generated_invoice_id))
        if plan.last_generated_invoice_id
        else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _to_brand_profile_response(profile: Any) -> schemas.SelfEmployedInvoiceBrandProfileResponse:
    return schemas.SelfEmployedInvoiceBrandProfileResponse(
        business_name=str(profile.business_name),
        logo_url=profile.logo_url,
        accent_color=profile.accent_color,
        payment_terms_note=profile.payment_terms_note,
        updated_at=profile.updated_at,
        message="Brand profile loaded.",
    )


def _to_reminder_event(item: Any) -> schemas.SelfEmployedInvoiceReminderEvent:
    return schemas.SelfEmployedInvoiceReminderEvent(
        id=uuid.UUID(str(item.id)),
        invoice_id=uuid.UUID(str(item.invoice_id)),
        reminder_type=item.reminder_type,
        channel=item.channel,
        status=item.status,
        message=item.message,
        created_at=item.created_at,
        sent_at=item.sent_at,
    )


def _to_calendar_event(item: Any) -> schemas.SelfEmployedCalendarEvent:
    return schemas.SelfEmployedCalendarEvent(
        id=uuid.UUID(str(item.id)),
        title=str(item.title),
        starts_at=_to_utc_datetime(item.starts_at),
        ends_at=_to_utc_datetime(item.ends_at) if item.ends_at else None,
        description=item.description,
        category=str(item.category or "general"),
        recipient_name=item.recipient_name,
        recipient_email=item.recipient_email,
        recipient_phone=item.recipient_phone,
        notify_in_app=bool(item.notify_in_app),
        notify_email=bool(item.notify_email),
        notify_sms=bool(item.notify_sms),
        notify_before_minutes=int(item.notify_before_minutes or 0),
        reminder_last_sent_at=_to_utc_datetime(item.reminder_last_sent_at) if item.reminder_last_sent_at else None,
        status=schemas.SelfEmployedCalendarEventStatus(item.status),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_calendar_reminder_event(item: Any) -> schemas.SelfEmployedCalendarReminderEvent:
    return schemas.SelfEmployedCalendarReminderEvent(
        id=uuid.UUID(str(item.id)),
        event_id=uuid.UUID(str(item.event_id)),
        reminder_type=item.reminder_type,
        channel=item.channel,
        status=item.status,
        message=item.message,
        created_at=item.created_at,
        sent_at=item.sent_at,
    )


def _validate_calendar_notification_channels(
    *,
    notify_in_app: bool,
    notify_email: bool,
    notify_sms: bool,
    recipient_email: str | None,
    recipient_phone: str | None,
) -> None:
    if not any([notify_in_app, notify_email, notify_sms]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one notification channel must be enabled.",
        )
    if notify_email and not recipient_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipient_email is required when notify_email=true",
        )
    if notify_sms and not recipient_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recipient_phone is required when notify_sms=true",
        )


async def _mark_overdue_invoices_for_user(
    db: AsyncSession,
    *,
    user_id: str,
) -> int:
    return await crud.mark_overdue_self_employed_invoices_for_user(
        db,
        user_id=user_id,
        as_of_date=datetime.datetime.now(datetime.UTC).date(),
    )


async def _resolve_branding_for_invoice(
    db: AsyncSession,
    *,
    user_id: str,
    payload: schemas.SelfEmployedInvoiceCreateRequest,
) -> tuple[str | None, str | None, str | None]:
    profile = await crud.get_brand_profile_for_user(db, user_id=user_id)
    business_name = payload.brand_business_name.strip() if payload.brand_business_name else None
    logo_url = payload.brand_logo_url.strip() if payload.brand_logo_url else None
    accent_color = _normalize_brand_accent_color(payload.brand_accent_color)

    if profile:
        if not business_name:
            business_name = str(profile.business_name)
        if not logo_url:
            logo_url = profile.logo_url
        if accent_color is None:
            accent_color = _normalize_brand_accent_color(profile.accent_color)
    return business_name, logo_url, accent_color


async def _create_invoice_from_recurring_plan(
    db: AsyncSession,
    *,
    user_id: str,
    plan: Any,
) -> schemas.SelfEmployedRecurringInvoicePlanRunResult:
    issue_date = max(plan.next_issue_date, datetime.datetime.now(datetime.UTC).date())
    due_date = issue_date + datetime.timedelta(days=max(SELF_EMPLOYED_INVOICE_DUE_DAYS, 1))
    cadence = schemas.SelfEmployedRecurringCadence(plan.cadence)
    line_items_raw = list(plan.line_items or [])
    line_items: list[dict[str, object]] = []
    for item in line_items_raw:
        description = str(item.get("description", "")).strip()
        if not description:
            continue
        line_items.append(
            {
                "description": description,
                "quantity": float(item.get("quantity", 1.0) or 1.0),
                "unit_price_gbp": float(item.get("unit_price_gbp", 0.0) or 0.0),
            }
        )
    if not line_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recurring plan {plan.id} has no valid line items",
        )

    brand_profile = await crud.get_brand_profile_for_user(db, user_id=user_id)
    invoice = await crud.create_self_employed_invoice(
        db,
        user_id=user_id,
        customer_name=plan.customer_name,
        customer_email=plan.customer_email,
        customer_phone=plan.customer_phone,
        customer_address=plan.customer_address,
        issue_date=issue_date,
        due_date=due_date,
        currency=str(plan.currency).upper(),
        tax_rate_percent=float(plan.tax_rate_percent),
        notes=plan.notes,
        payment_link_url=None,
        payment_link_provider=None,
        recurring_plan_id=str(plan.id),
        brand_business_name=str(brand_profile.business_name) if brand_profile else None,
        brand_logo_url=brand_profile.logo_url if brand_profile else None,
        brand_accent_color=_normalize_brand_accent_color(brand_profile.accent_color) if brand_profile else None,
        lines=line_items,
    )
    invoice = await crud.update_self_employed_invoice_payment_link(
        db,
        invoice,
        payment_link_url=_build_self_employed_payment_link(str(invoice.id)),
        payment_link_provider=SELF_EMPLOYED_PAYMENT_LINK_PROVIDER,
    )
    invoice_id = str(invoice.id)
    invoice_number = str(invoice.invoice_number)
    next_issue_date = _next_cadence_date(date_value=issue_date, cadence=cadence)
    await crud.mark_recurring_plan_generated(
        db,
        plan,
        next_issue_date=next_issue_date,
        last_generated_invoice_id=invoice_id,
    )
    return schemas.SelfEmployedRecurringInvoicePlanRunResult(
        plan_id=uuid.UUID(str(plan.id)),
        invoice_id=uuid.UUID(invoice_id),
        invoice_number=invoice_number,
        next_issue_date=next_issue_date,
        message="Recurring invoice generated.",
    )


async def _load_lead_report(
    db: AsyncSession,
    partner_id: uuid.UUID | None,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    statuses: list[str] | None,
) -> schemas.LeadReportResponse:
    start_at, end_before = _build_report_window(start_date, end_date)
    total_leads, unique_users, by_partner_rows = await crud.get_lead_report(
        db,
        partner_id=str(partner_id) if partner_id else None,
        start_at=start_at,
        end_before=end_before,
        statuses=statuses,
    )
    return schemas.LeadReportResponse(
        period_start=start_date,
        period_end=end_date,
        total_leads=total_leads,
        unique_users=unique_users,
        by_partner=[
            schemas.LeadReportByPartner(
                partner_id=uuid.UUID(partner_id_str),
                partner_name=partner_name,
                leads_count=leads_count,
                unique_users=partner_unique_users,
            )
            for (
                partner_id_str,
                partner_name,
                leads_count,
                partner_unique_users,
            ) in by_partner_rows
        ],
    )


async def _load_billing_report(
    db: AsyncSession,
    partner_id: uuid.UUID | None,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    statuses: list[str],
) -> schemas.BillingReportResponse:
    start_at, end_before = _build_report_window(start_date, end_date)
    (
        total_leads,
        unique_users,
        qualified_leads,
        converted_leads,
        by_partner_rows,
    ) = await crud.get_billing_report(
        db,
        partner_id=str(partner_id) if partner_id else None,
        start_at=start_at,
        end_before=end_before,
        statuses=statuses,
    )

    by_partner: list[schemas.BillingReportByPartner] = []
    total_amount_gbp = 0.0
    for (
        partner_id_str,
        partner_name,
        qualified_fee,
        converted_fee,
        partner_qualified_leads,
        partner_converted_leads,
        partner_unique_users,
    ) in by_partner_rows:
        amount_gbp = round(
            (partner_qualified_leads * qualified_fee) + (partner_converted_leads * converted_fee),
            2,
        )
        total_amount_gbp += amount_gbp
        by_partner.append(
            schemas.BillingReportByPartner(
                partner_id=uuid.UUID(partner_id_str),
                partner_name=partner_name,
                qualified_leads=partner_qualified_leads,
                converted_leads=partner_converted_leads,
                unique_users=partner_unique_users,
                qualified_lead_fee_gbp=qualified_fee,
                converted_lead_fee_gbp=converted_fee,
                amount_gbp=amount_gbp,
            )
        )

    return schemas.BillingReportResponse(
        period_start=start_date,
        period_end=end_date,
        currency="GBP",
        total_leads=total_leads,
        qualified_leads=qualified_leads,
        converted_leads=converted_leads,
        unique_users=unique_users,
        total_amount_gbp=round(total_amount_gbp, 2),
        by_partner=by_partner,
    )


def _build_csv_report(report: schemas.LeadReportResponse) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "row_type",
            "period_start",
            "period_end",
            "partner_id",
            "partner_name",
            "leads_count",
            "unique_users",
        ]
    )
    writer.writerow(
        [
            "SUMMARY",
            report.period_start.isoformat() if report.period_start else "",
            report.period_end.isoformat() if report.period_end else "",
            "",
            "ALL_PARTNERS",
            report.total_leads,
            report.unique_users,
        ]
    )
    for row in report.by_partner:
        writer.writerow(
            [
                "PARTNER",
                report.period_start.isoformat() if report.period_start else "",
                report.period_end.isoformat() if report.period_end else "",
                str(row.partner_id),
                row.partner_name,
                row.leads_count,
                row.unique_users,
            ]
        )
    return output.getvalue()


def _csv_response(report: schemas.LeadReportResponse) -> Response:
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
    filename = f"lead_report_{timestamp}.csv"
    return Response(
        content=_build_csv_report(report),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_billing_csv_report(report: schemas.BillingReportResponse) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "row_type",
            "period_start",
            "period_end",
            "currency",
            "partner_id",
            "partner_name",
            "qualified_leads",
            "converted_leads",
            "total_leads",
            "unique_users",
            "qualified_lead_fee_gbp",
            "converted_lead_fee_gbp",
            "amount_gbp",
        ]
    )
    writer.writerow(
        [
            "SUMMARY",
            report.period_start.isoformat() if report.period_start else "",
            report.period_end.isoformat() if report.period_end else "",
            report.currency,
            "",
            "ALL_PARTNERS",
            report.qualified_leads,
            report.converted_leads,
            report.total_leads,
            report.unique_users,
            "",
            "",
            f"{report.total_amount_gbp:.2f}",
        ]
    )
    for row in report.by_partner:
        writer.writerow(
            [
                "PARTNER",
                report.period_start.isoformat() if report.period_start else "",
                report.period_end.isoformat() if report.period_end else "",
                report.currency,
                str(row.partner_id),
                row.partner_name,
                row.qualified_leads,
                row.converted_leads,
                row.qualified_leads + row.converted_leads,
                row.unique_users,
                f"{row.qualified_lead_fee_gbp:.2f}",
                f"{row.converted_lead_fee_gbp:.2f}",
                f"{row.amount_gbp:.2f}",
            ]
        )
    return output.getvalue()


def _billing_csv_response(report: schemas.BillingReportResponse) -> Response:
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
    filename = f"lead_billing_report_{timestamp}.csv"
    return Response(
        content=_build_billing_csv_report(report),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _render_simple_pdf(lines: list[str]) -> bytes:
    safe_lines = [line for line in lines if line.strip()]
    y_position = 800
    text_operations: list[str] = ["BT", "/F1 10 Tf"]
    for line in safe_lines:
        if y_position < 60:
            break
        text_operations.append(f"1 0 0 1 48 {y_position} Tm ({_escape_pdf_text(line)}) Tj")
        y_position -= 15
    text_operations.append("ET")
    stream = "\n".join(text_operations).encode("utf-8")

    objects: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n"
            b"endobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        (
            f"5 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("utf-8")
            + stream
            + b"\nendstream\nendobj\n"
        ),
    ]

    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("utf-8")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode("utf-8")
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("utf-8")
    pdf += f"startxref\n{xref_start}\n%%EOF\n".encode("utf-8")
    return pdf


def _build_invoice_pdf(invoice: schemas.BillingInvoiceDetail) -> bytes:
    invoice_date = invoice.created_at.date().isoformat()
    lines = [
        "Billing Invoice",
        f"Invoice number: {invoice.invoice_number}",
        f"Invoice date: {invoice_date}",
        f"Due date: {invoice.due_date.isoformat()}",
        f"Status: {invoice.status.value}",
        f"Currency: {invoice.currency}",
        (
            f"Billing period: {(invoice.period_start.isoformat() if invoice.period_start else 'N/A')} "
            f"to {(invoice.period_end.isoformat() if invoice.period_end else 'N/A')}"
        ),
        "",
        "Line items",
    ]

    if not invoice.lines:
        lines.append("No billable line items found for this invoice snapshot.")
    for line in invoice.lines:
        if line.qualified_leads > 0:
            lines.append(
                (
                    f"- {line.partner_name} / qualified leads: {line.qualified_leads} x "
                    f"{line.qualified_lead_fee_gbp:.2f} = "
                    f"{line.qualified_leads * line.qualified_lead_fee_gbp:.2f} {invoice.currency}"
                )
            )
        if line.converted_leads > 0:
            lines.append(
                (
                    f"- {line.partner_name} / converted leads: {line.converted_leads} x "
                    f"{line.converted_lead_fee_gbp:.2f} = "
                    f"{line.converted_leads * line.converted_lead_fee_gbp:.2f} {invoice.currency}"
                )
            )
    lines.extend(["", f"Total: {invoice.total_amount_gbp:.2f} {invoice.currency}"])
    return _render_simple_pdf(lines)


def _invoice_pdf_response(invoice: schemas.BillingInvoiceDetail) -> Response:
    filename = f"{invoice.invoice_number}.pdf"
    return Response(
        content=_build_invoice_pdf(invoice),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_accounting_csv(invoice: schemas.BillingInvoiceDetail, *, target: Literal["xero", "quickbooks"]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    invoice_date = invoice.created_at.date().isoformat()
    due_date = invoice.due_date.isoformat()

    if target == "xero":
        writer.writerow(
            [
                "ContactName",
                "InvoiceNumber",
                "InvoiceDate",
                "DueDate",
                "Description",
                "Quantity",
                "UnitAmount",
                "LineAmount",
                "TaxType",
                "AccountCode",
                "Currency",
            ]
        )
    else:
        writer.writerow(
            [
                "Customer",
                "InvoiceNo",
                "InvoiceDate",
                "DueDate",
                "Item",
                "Description",
                "Qty",
                "Rate",
                "Amount",
                "Class",
                "Currency",
            ]
        )

    has_rows = False
    for line in invoice.lines:
        partner_name = line.partner_name
        if line.qualified_leads > 0:
            amount = round(line.qualified_leads * line.qualified_lead_fee_gbp, 2)
            has_rows = True
            if target == "xero":
                writer.writerow(
                    [
                        partner_name,
                        invoice.invoice_number,
                        invoice_date,
                        due_date,
                        "Qualified leads",
                        line.qualified_leads,
                        f"{line.qualified_lead_fee_gbp:.2f}",
                        f"{amount:.2f}",
                        "NONE",
                        "200",
                        invoice.currency,
                    ]
                )
            else:
                writer.writerow(
                    [
                        partner_name,
                        invoice.invoice_number,
                        invoice_date,
                        due_date,
                        "QualifiedLead",
                        "Qualified leads",
                        line.qualified_leads,
                        f"{line.qualified_lead_fee_gbp:.2f}",
                        f"{amount:.2f}",
                        "Leads",
                        invoice.currency,
                    ]
                )

        if line.converted_leads > 0:
            amount = round(line.converted_leads * line.converted_lead_fee_gbp, 2)
            has_rows = True
            if target == "xero":
                writer.writerow(
                    [
                        partner_name,
                        invoice.invoice_number,
                        invoice_date,
                        due_date,
                        "Converted leads",
                        line.converted_leads,
                        f"{line.converted_lead_fee_gbp:.2f}",
                        f"{amount:.2f}",
                        "NONE",
                        "200",
                        invoice.currency,
                    ]
                )
            else:
                writer.writerow(
                    [
                        partner_name,
                        invoice.invoice_number,
                        invoice_date,
                        due_date,
                        "ConvertedLead",
                        "Converted leads",
                        line.converted_leads,
                        f"{line.converted_lead_fee_gbp:.2f}",
                        f"{amount:.2f}",
                        "Leads",
                        invoice.currency,
                    ]
                )

    if not has_rows:
        if target == "xero":
            writer.writerow(
                [
                    "No billable lines",
                    invoice.invoice_number,
                    invoice_date,
                    due_date,
                    "No billable lines",
                    1,
                    "0.00",
                    "0.00",
                    "NONE",
                    "200",
                    invoice.currency,
                ]
            )
        else:
            writer.writerow(
                [
                    "No billable lines",
                    invoice.invoice_number,
                    invoice_date,
                    due_date,
                    "NoLines",
                    "No billable lines",
                    1,
                    "0.00",
                    "0.00",
                    "Leads",
                    invoice.currency,
                ]
            )

    return output.getvalue()


def _accounting_csv_response(
    invoice: schemas.BillingInvoiceDetail,
    *,
    target: Literal["xero", "quickbooks"],
) -> Response:
    filename = f"{invoice.invoice_number}_{target}.csv"
    return Response(
        content=_build_accounting_csv(invoice, target=target),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_self_employed_invoice_pdf(invoice: schemas.SelfEmployedInvoiceDetail) -> bytes:
    lines = []
    if invoice.brand_business_name:
        lines.append(f"Brand: {invoice.brand_business_name}")
    if invoice.brand_accent_color:
        lines.append(f"Brand accent: {invoice.brand_accent_color}")
    if invoice.brand_logo_url:
        lines.append(f"Brand logo: {invoice.brand_logo_url}")
    lines.extend(
        [
            "Self-Employed Client Invoice",
            f"Invoice number: {invoice.invoice_number}",
            f"Issue date: {invoice.issue_date.isoformat()}",
            f"Due date: {invoice.due_date.isoformat()}",
            f"Status: {invoice.status.value}",
            f"Customer: {invoice.customer_name}",
            f"Customer email: {invoice.customer_email or 'N/A'}",
            f"Customer phone: {invoice.customer_phone or 'N/A'}",
            f"Currency: {invoice.currency}",
        ]
    )
    if invoice.payment_link_url:
        lines.append(f"Payment link: {invoice.payment_link_url}")
    lines.extend(["", "Line items"])
    for item in invoice.lines:
        lines.append(f"- {item.description}: {item.quantity:.2f} x {item.unit_price_gbp:.2f} = {item.line_total_gbp:.2f} {invoice.currency}")
    lines.extend(
        [
            "",
            f"Subtotal: {invoice.subtotal_gbp:.2f} {invoice.currency}",
            f"Tax ({invoice.tax_rate_percent:.2f}%): {invoice.tax_amount_gbp:.2f} {invoice.currency}",
            f"Total: {invoice.total_amount_gbp:.2f} {invoice.currency}",
        ]
    )
    if invoice.notes:
        lines.extend(["", f"Notes: {invoice.notes}"])
    return _render_simple_pdf(lines)


def _self_employed_invoice_pdf_response(invoice: schemas.SelfEmployedInvoiceDetail) -> Response:
    filename = f"{invoice.invoice_number}.pdf"
    return Response(
        content=_build_self_employed_invoice_pdf(invoice),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_self_employed_invoice_csv(invoice: schemas.SelfEmployedInvoiceDetail) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "invoice_number",
            "issue_date",
            "due_date",
            "status",
            "customer_name",
            "customer_phone",
            "description",
            "quantity",
            "unit_price_gbp",
            "line_total_gbp",
            "currency",
            "payment_link_url",
            "brand_business_name",
            "brand_accent_color",
        ]
    )
    for item in invoice.lines:
        writer.writerow(
            [
                invoice.invoice_number,
                invoice.issue_date.isoformat(),
                invoice.due_date.isoformat(),
                invoice.status.value,
                invoice.customer_name,
                invoice.customer_phone or "",
                item.description,
                f"{item.quantity:.2f}",
                f"{item.unit_price_gbp:.2f}",
                f"{item.line_total_gbp:.2f}",
                invoice.currency,
                invoice.payment_link_url or "",
                invoice.brand_business_name or "",
                invoice.brand_accent_color or "",
            ]
        )
    writer.writerow(
        [
            invoice.invoice_number,
            invoice.issue_date.isoformat(),
            invoice.due_date.isoformat(),
            invoice.status.value,
            invoice.customer_name,
            invoice.customer_phone or "",
            "TOTAL",
            "",
            "",
            f"{invoice.total_amount_gbp:.2f}",
            invoice.currency,
            invoice.payment_link_url or "",
            invoice.brand_business_name or "",
            invoice.brand_accent_color or "",
        ]
    )
    return output.getvalue()


def _self_employed_invoice_csv_response(invoice: schemas.SelfEmployedInvoiceDetail) -> Response:
    filename = f"{invoice.invoice_number}.csv"
    return Response(
        content=_build_self_employed_invoice_csv(invoice),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/partners", response_model=List[schemas.Partner])
async def list_partners(
    service_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_partners(db, service_type=service_type)


@app.get("/partners/{partner_id}", response_model=schemas.Partner)
async def get_partner_details(
    partner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    partner = await crud.get_partner_by_id(db, str(partner_id))
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner


@app.patch("/partners/{partner_id}/pricing", response_model=schemas.Partner)
async def update_partner_pricing(
    partner_id: uuid.UUID,
    payload: schemas.PartnerPricingUpdateRequest,
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    partner = await crud.get_partner_by_id(db, str(partner_id))
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    updated = await crud.update_partner_pricing(
        db,
        partner=partner,
        qualified_lead_fee_gbp=payload.qualified_lead_fee_gbp,
        converted_lead_fee_gbp=payload.converted_lead_fee_gbp,
    )
    await log_audit_event(
        user_id=user_id,
        action="partner.pricing.updated",
        details={
            "partner_id": str(partner_id),
            "qualified_lead_fee_gbp": payload.qualified_lead_fee_gbp,
            "converted_lead_fee_gbp": payload.converted_lead_fee_gbp,
        },
    )
    return updated


@app.post(
    "/partners/{partner_id}/handoff",
    response_model=schemas.HandoffResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def initiate_handoff(
    partner_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    partner = await crud.get_partner_by_id(db, str(partner_id))
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    partner_db_id = str(partner.id)
    partner_name = partner.name

    lead, duplicated = await crud.create_or_get_handoff_lead(
        db,
        user_id=user_id,
        partner_id=partner_db_id,
    )

    if duplicated:
        return schemas.HandoffResponse(
            message=f"Handoff to {partner_name} already initiated recently.",
            lead_id=uuid.UUID(str(lead.id)),
            duplicated=True,
        )

    audit_event_id = await log_audit_event(
        user_id=user_id,
        action="partner.handoff.initiated",
        details={
            "lead_id": str(lead.id),
            "partner_id": partner_db_id,
            "partner_name": partner_name,
        },
    )

    return schemas.HandoffResponse(
        message=f"Handoff to {partner_name} initiated.",
        lead_id=uuid.UUID(str(lead.id)),
        audit_event_id=audit_event_id,
    )


@app.patch("/leads/{lead_id}/status", response_model=schemas.LeadStatusUpdateResponse)
async def update_lead_status(
    lead_id: uuid.UUID,
    payload: schemas.LeadStatusUpdateRequest,
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    lead = await crud.get_handoff_lead_by_id(db, str(lead_id))
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    previous_status = lead.status
    _validate_status_transition(previous_status, payload.status)
    if payload.status.value != previous_status:
        lead = await crud.update_handoff_lead_status(db, lead=lead, status=payload.status.value)
        await log_audit_event(
            user_id=user_id,
            action="partner.handoff.status.updated",
            details={
                "lead_id": str(lead.id),
                "from_status": previous_status,
                "to_status": payload.status.value,
            },
        )

    return schemas.LeadStatusUpdateResponse(
        lead_id=uuid.UUID(str(lead.id)),
        status=schemas.LeadStatus(lead.status),
        updated_at=lead.updated_at,
    )


@app.get("/leads", response_model=schemas.LeadListResponse)
async def list_leads(
    partner_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[schemas.LeadStatus] = Query(default=None, alias="status"),
    user_id: Optional[str] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    start_at, end_before = _build_report_window(start_date, end_date)
    total, rows = await crud.list_handoff_leads(
        db,
        partner_id=str(partner_id) if partner_id else None,
        status=status_filter.value if status_filter else None,
        user_id=user_id,
        start_at=start_at,
        end_before=end_before,
        limit=limit,
        offset=offset,
    )
    return schemas.LeadListResponse(
        total=total,
        items=[
            schemas.LeadListItem(
                id=uuid.UUID(lead_id),
                user_id=lead_user_id,
                partner_id=uuid.UUID(lead_partner_id),
                partner_name=partner_name,
                status=schemas.LeadStatus(lead_status),
                created_at=created_at,
                updated_at=updated_at,
            )
            for (
                lead_id,
                lead_user_id,
                lead_partner_id,
                partner_name,
                lead_status,
                created_at,
                updated_at,
            ) in rows
        ],
    )


@app.post(
    "/self-employed/invoices",
    response_model=schemas.SelfEmployedInvoiceDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_self_employed_invoice(
    payload: schemas.SelfEmployedInvoiceCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    issue_date = payload.issue_date or datetime.datetime.now(datetime.UTC).date()
    due_date = payload.due_date or (issue_date + datetime.timedelta(days=max(SELF_EMPLOYED_INVOICE_DUE_DAYS, 1)))
    if due_date < issue_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="due_date cannot be earlier than issue_date")

    customer_name = payload.customer_name.strip()
    if not customer_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_name cannot be empty")

    line_items: list[dict[str, object]] = []
    for line in payload.lines:
        description = line.description.strip()
        if not description:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="line item description cannot be empty")
        line_items.append(
            {
                "description": description,
                "quantity": line.quantity,
                "unit_price_gbp": line.unit_price_gbp,
            }
        )

    brand_business_name, brand_logo_url, brand_accent_color = await _resolve_branding_for_invoice(
        db,
        user_id=user_id,
        payload=payload,
    )
    invoice = await crud.create_self_employed_invoice(
        db,
        user_id=user_id,
        customer_name=customer_name,
        customer_email=payload.customer_email.strip() if payload.customer_email else None,
        customer_phone=payload.customer_phone.strip() if payload.customer_phone else None,
        customer_address=payload.customer_address.strip() if payload.customer_address else None,
        issue_date=issue_date,
        due_date=due_date,
        currency=payload.currency.strip().upper(),
        tax_rate_percent=payload.tax_rate_percent,
        notes=payload.notes.strip() if payload.notes else None,
        payment_link_url=None,
        payment_link_provider=None,
        recurring_plan_id=None,
        brand_business_name=brand_business_name,
        brand_logo_url=brand_logo_url,
        brand_accent_color=brand_accent_color,
        lines=line_items,
    )
    invoice = await crud.update_self_employed_invoice_payment_link(
        db,
        invoice,
        payment_link_url=_build_self_employed_payment_link(str(invoice.id)),
        payment_link_provider=SELF_EMPLOYED_PAYMENT_LINK_PROVIDER,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.created",
        details={
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "total_amount_gbp": invoice.total_amount_gbp,
            "status": invoice.status,
            "payment_link_provider": invoice.payment_link_provider,
        },
    )
    return await _load_self_employed_invoice_detail(
        db,
        invoice_id=uuid.UUID(str(invoice.id)),
        user_id=user_id,
    )


@app.get("/self-employed/invoices", response_model=schemas.SelfEmployedInvoiceListResponse)
async def list_self_employed_invoices(
    status_filter: Optional[schemas.SelfEmployedInvoiceStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _mark_overdue_invoices_for_user(db, user_id=user_id)
    total, rows = await crud.list_self_employed_invoices_for_user(
        db,
        user_id=user_id,
        status=status_filter.value if status_filter else None,
        limit=limit,
        offset=offset,
    )
    return schemas.SelfEmployedInvoiceListResponse(
        total=total,
        items=[_to_self_employed_invoice_summary(item) for item in rows],
    )


@app.get("/self-employed/invoices/{invoice_id}", response_model=schemas.SelfEmployedInvoiceDetail)
async def get_self_employed_invoice(
    invoice_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _mark_overdue_invoices_for_user(db, user_id=user_id)
    return await _load_self_employed_invoice_detail(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
    )


@app.patch("/self-employed/invoices/{invoice_id}/status", response_model=schemas.SelfEmployedInvoiceDetail)
async def update_self_employed_invoice_status(
    invoice_id: uuid.UUID,
    payload: schemas.SelfEmployedInvoiceStatusUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _mark_overdue_invoices_for_user(db, user_id=user_id)
    invoice = await crud.get_self_employed_invoice_by_id_for_user(
        db,
        invoice_id=str(invoice_id),
        user_id=user_id,
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Self-employed invoice not found")

    _validate_self_employed_invoice_status_transition(invoice.status, payload.status)
    previous_status = invoice.status
    if payload.status.value != invoice.status:
        invoice = await crud.update_self_employed_invoice_status(
            db,
            invoice,
            status=payload.status.value,
        )
        await log_audit_event(
            user_id=user_id,
            action="self_employed.invoice.status.updated",
            details={
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "from_status": previous_status,
                "to_status": payload.status.value,
            },
        )
    return await _load_self_employed_invoice_detail(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
    )


@app.get("/self-employed/invoices/{invoice_id}/pdf")
async def download_self_employed_invoice_pdf(
    invoice_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    invoice = await _load_self_employed_invoice_detail(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.pdf_downloaded",
        details={"invoice_id": str(invoice_id), "invoice_number": invoice.invoice_number},
    )
    return _self_employed_invoice_pdf_response(invoice)


@app.get("/self-employed/invoices/{invoice_id}/csv")
async def download_self_employed_invoice_csv(
    invoice_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    invoice = await _load_self_employed_invoice_detail(
        db,
        invoice_id=invoice_id,
        user_id=user_id,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.csv_downloaded",
        details={"invoice_id": str(invoice_id), "invoice_number": invoice.invoice_number},
    )
    return _self_employed_invoice_csv_response(invoice)


@app.get(
    "/self-employed/invoicing/brand",
    response_model=schemas.SelfEmployedInvoiceBrandProfileResponse,
)
async def get_self_employed_invoice_brand_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    profile = await crud.get_brand_profile_for_user(db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile is not configured")
    return _to_brand_profile_response(profile)


@app.put(
    "/self-employed/invoicing/brand",
    response_model=schemas.SelfEmployedInvoiceBrandProfileResponse,
)
async def upsert_self_employed_invoice_brand_profile(
    payload: schemas.SelfEmployedInvoiceBrandProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    accent_color = _normalize_brand_accent_color(payload.accent_color)
    profile = await crud.upsert_brand_profile_for_user(
        db,
        user_id=user_id,
        business_name=payload.business_name.strip(),
        logo_url=payload.logo_url.strip() if payload.logo_url else None,
        accent_color=accent_color,
        payment_terms_note=payload.payment_terms_note.strip() if payload.payment_terms_note else None,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.brand_profile.upserted",
        details={
            "business_name": profile.business_name,
            "accent_color": profile.accent_color,
        },
    )
    response = _to_brand_profile_response(profile)
    return response.model_copy(update={"message": "Brand profile saved."})


@app.post(
    "/self-employed/invoicing/recurring-plans",
    response_model=schemas.SelfEmployedRecurringInvoicePlanSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_self_employed_recurring_plan(
    payload: schemas.SelfEmployedRecurringInvoicePlanCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    line_items: list[dict[str, object]] = []
    for line in payload.lines:
        description = line.description.strip()
        if not description:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="line item description cannot be empty")
        line_items.append(
            {
                "description": description,
                "quantity": float(line.quantity),
                "unit_price_gbp": float(line.unit_price_gbp),
            }
        )

    issue_date = payload.next_issue_date or datetime.datetime.now(datetime.UTC).date()
    plan = await crud.create_recurring_invoice_plan(
        db,
        user_id=user_id,
        customer_name=payload.customer_name.strip(),
        customer_email=payload.customer_email.strip() if payload.customer_email else None,
        customer_phone=payload.customer_phone.strip() if payload.customer_phone else None,
        customer_address=payload.customer_address.strip() if payload.customer_address else None,
        currency=payload.currency.strip().upper(),
        tax_rate_percent=float(payload.tax_rate_percent),
        notes=payload.notes.strip() if payload.notes else None,
        line_items=line_items,
        cadence=payload.cadence.value,
        next_issue_date=issue_date,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.recurring_plan.created",
        details={
            "plan_id": str(plan.id),
            "cadence": plan.cadence,
            "next_issue_date": plan.next_issue_date.isoformat(),
        },
    )
    return _to_recurring_plan_summary(plan)


@app.get(
    "/self-employed/invoicing/recurring-plans",
    response_model=schemas.SelfEmployedRecurringInvoicePlanListResponse,
)
async def list_self_employed_recurring_plans(
    active_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total, rows = await crud.list_recurring_invoice_plans_for_user(
        db,
        user_id=user_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return schemas.SelfEmployedRecurringInvoicePlanListResponse(
        total=total,
        items=[_to_recurring_plan_summary(item) for item in rows],
    )


@app.patch(
    "/self-employed/invoicing/recurring-plans/{plan_id}",
    response_model=schemas.SelfEmployedRecurringInvoicePlanSummary,
)
async def update_self_employed_recurring_plan_status(
    plan_id: uuid.UUID,
    payload: schemas.SelfEmployedRecurringInvoicePlanStatusUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    plan = await crud.get_recurring_invoice_plan_for_user(
        db,
        plan_id=str(plan_id),
        user_id=user_id,
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring plan not found")
    updated = await crud.update_recurring_invoice_plan_activity(
        db,
        plan,
        active=payload.active,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.recurring_plan.updated",
        details={"plan_id": str(plan_id), "active": payload.active},
    )
    return _to_recurring_plan_summary(updated)


@app.post(
    "/self-employed/invoicing/recurring-plans/{plan_id}/run",
    response_model=schemas.SelfEmployedRecurringInvoicePlanRunResult,
)
async def run_self_employed_recurring_plan_once(
    plan_id: uuid.UUID,
    force: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    plan = await crud.get_recurring_invoice_plan_for_user(
        db,
        plan_id=str(plan_id),
        user_id=user_id,
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring plan not found")
    if not bool(plan.active):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recurring plan is inactive")
    today = datetime.datetime.now(datetime.UTC).date()
    if not force and plan.next_issue_date > today:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Recurring plan is not due yet (next_issue_date={plan.next_issue_date.isoformat()})",
        )

    run_result = await _create_invoice_from_recurring_plan(
        db,
        user_id=user_id,
        plan=plan,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.recurring_plan.executed",
        details={
            "plan_id": str(plan_id),
            "invoice_id": str(run_result.invoice_id),
            "invoice_number": run_result.invoice_number,
            "next_issue_date": run_result.next_issue_date.isoformat(),
        },
    )
    return run_result


@app.post(
    "/self-employed/invoicing/recurring-plans/run-due",
    response_model=schemas.SelfEmployedRecurringInvoicePlanRunBatchResponse,
)
async def run_due_self_employed_recurring_plans(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.datetime.now(datetime.UTC).date()
    plans = await crud.list_due_recurring_invoice_plans_for_user(
        db,
        user_id=user_id,
        as_of_date=today,
    )
    generated: list[schemas.SelfEmployedRecurringInvoicePlanRunResult] = []
    for plan in plans:
        run_result = await _create_invoice_from_recurring_plan(
            db,
            user_id=user_id,
            plan=plan,
        )
        generated.append(run_result)
        await log_audit_event(
            user_id=user_id,
            action="self_employed.invoice.recurring_plan.executed",
            details={
                "plan_id": str(plan.id),
                "invoice_id": str(run_result.invoice_id),
                "invoice_number": run_result.invoice_number,
                "next_issue_date": run_result.next_issue_date.isoformat(),
            },
        )

    note = "No due recurring plans." if not generated else "Generated due recurring invoices."
    return schemas.SelfEmployedRecurringInvoicePlanRunBatchResponse(
        generated_count=len(generated),
        generated=generated,
        note=note,
    )


@app.get(
    "/self-employed/invoicing/reminders/readiness",
    response_model=schemas.SelfEmployedReminderDeliveryReadinessResponse,
)
async def get_self_employed_reminder_delivery_readiness(
    _user_id: str = Depends(get_current_user_id),
):
    return _build_reminder_delivery_readiness_snapshot()


@app.post(
    "/self-employed/invoicing/reminders/smoke-check",
    response_model=schemas.SelfEmployedReminderSmokeCheckResponse,
)
async def run_self_employed_reminder_delivery_smoke_check(
    payload: schemas.SelfEmployedReminderSmokeCheckRequest,
    user_id: str = Depends(get_current_user_id),
):
    readiness = _build_reminder_delivery_readiness_snapshot()
    selected_channels: list[Literal["email", "sms"]]
    if payload.channel == "both":
        selected_channels = ["email", "sms"]
    else:
        selected_channels = [payload.channel]

    results: list[schemas.SelfEmployedReminderSmokeCheckChannelResult] = []
    for channel in selected_channels:
        channel_state = readiness.email if channel == "email" else readiness.sms
        if not channel_state.enabled:
            results.append(
                schemas.SelfEmployedReminderSmokeCheckChannelResult(
                    channel=channel,
                    provider=channel_state.provider,
                    enabled=channel_state.enabled,
                    configured=channel_state.configured,
                    network_check_performed=False,
                    delivery_status="skipped",
                    detail=f"{channel} channel is disabled.",
                )
            )
            continue
        if not channel_state.configured:
            results.append(
                schemas.SelfEmployedReminderSmokeCheckChannelResult(
                    channel=channel,
                    provider=channel_state.provider,
                    enabled=channel_state.enabled,
                    configured=channel_state.configured,
                    network_check_performed=False,
                    delivery_status="failed",
                    detail=_truncate_text("; ".join(channel_state.warnings) or f"{channel} channel is misconfigured."),
                )
            )
            continue
        if not payload.perform_network_check:
            results.append(
                schemas.SelfEmployedReminderSmokeCheckChannelResult(
                    channel=channel,
                    provider=channel_state.provider,
                    enabled=channel_state.enabled,
                    configured=channel_state.configured,
                    network_check_performed=False,
                    delivery_status="skipped",
                    detail="Configuration is valid. Network check was skipped.",
                )
            )
            continue

        if channel == "email":
            recipient_email = payload.test_recipient_email.strip() if payload.test_recipient_email else None
            if not recipient_email:
                results.append(
                    schemas.SelfEmployedReminderSmokeCheckChannelResult(
                        channel=channel,
                        provider=channel_state.provider,
                        enabled=channel_state.enabled,
                        configured=channel_state.configured,
                        network_check_performed=True,
                        delivery_status="failed",
                        detail="Provide test_recipient_email for email smoke check.",
                    )
                )
                continue
            delivery_status, detail = await _dispatch_invoice_reminder_email(
                invoice_id="smoke-check",
                invoice_number="SMOKE-CHECK-EMAIL",
                reminder_type=payload.reminder_type,
                message="Smoke-check reminder dispatch for email channel.",
                recipient_email=recipient_email,
            )
        else:
            recipient_phone = payload.test_recipient_phone.strip() if payload.test_recipient_phone else None
            if not recipient_phone:
                results.append(
                    schemas.SelfEmployedReminderSmokeCheckChannelResult(
                        channel=channel,
                        provider=channel_state.provider,
                        enabled=channel_state.enabled,
                        configured=channel_state.configured,
                        network_check_performed=True,
                        delivery_status="failed",
                        detail="Provide test_recipient_phone for SMS smoke check.",
                    )
                )
                continue
            delivery_status, detail = await _dispatch_invoice_reminder_sms(
                invoice_id="smoke-check",
                invoice_number="SMOKE-CHECK-SMS",
                reminder_type=payload.reminder_type,
                message="Smoke-check reminder dispatch for SMS channel.",
                recipient_phone=recipient_phone,
            )

        results.append(
            schemas.SelfEmployedReminderSmokeCheckChannelResult(
                channel=channel,
                provider=channel_state.provider,
                enabled=channel_state.enabled,
                configured=channel_state.configured,
                network_check_performed=True,
                delivery_status=delivery_status if delivery_status in {"sent", "failed"} else "failed",
                detail=_truncate_text(detail),
            )
        )

    passed = all(item.delivery_status != "failed" for item in results)
    await log_audit_event(
        user_id=user_id,
        action="self_employed.invoice.reminders.smoke_check",
        details={
            "requested_channel": payload.channel,
            "perform_network_check": payload.perform_network_check,
            "passed": passed,
            "results": [item.model_dump() for item in results],
        },
    )
    return schemas.SelfEmployedReminderSmokeCheckResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        requested_channel=payload.channel,
        perform_network_check=payload.perform_network_check,
        results=results,
        passed=passed,
    )


@app.post(
    "/self-employed/invoicing/reminders/run",
    response_model=schemas.SelfEmployedInvoiceReminderRunResponse,
)
async def run_self_employed_invoice_reminders(
    due_in_days: int = Query(default=SELF_EMPLOYED_REMINDER_DUE_SOON_DAYS, ge=1, le=30),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _mark_overdue_invoices_for_user(db, user_id=user_id)
    issued_total, issued_rows = await crud.list_self_employed_invoices_for_user(
        db,
        user_id=user_id,
        status=schemas.SelfEmployedInvoiceStatus.issued.value,
        limit=500,
        offset=0,
    )
    overdue_total, overdue_rows = await crud.list_self_employed_invoices_for_user(
        db,
        user_id=user_id,
        status=schemas.SelfEmployedInvoiceStatus.overdue.value,
        limit=500,
        offset=0,
    )
    _ = issued_total + overdue_total  # Retained for future pagination improvements.
    today = datetime.datetime.now(datetime.UTC).date()
    due_soon_cutoff = today + datetime.timedelta(days=due_in_days)
    now = datetime.datetime.now(datetime.UTC)

    invoice_candidates = [
        {
            "id": str(item.id),
            "status": str(item.status),
            "due_date": item.due_date,
            "invoice_number": str(item.invoice_number),
            "customer_email": item.customer_email,
            "customer_phone": item.customer_phone,
            "reminder_last_sent_at": item.reminder_last_sent_at,
        }
        for item in [*issued_rows, *overdue_rows]
    ]

    reminders: list[schemas.SelfEmployedInvoiceReminderEvent] = []
    for invoice_candidate in invoice_candidates:
        reminder_type: Literal["due_soon", "overdue"] | None = None
        if invoice_candidate["status"] == schemas.SelfEmployedInvoiceStatus.overdue.value:
            reminder_type = "overdue"
        elif today <= invoice_candidate["due_date"] <= due_soon_cutoff:
            reminder_type = "due_soon"
        if reminder_type is None:
            continue
        if invoice_candidate["reminder_last_sent_at"] and (
            now - invoice_candidate["reminder_last_sent_at"]
        ).total_seconds() < 24 * 3600:
            continue

        message = (
            f"Invoice {invoice_candidate['invoice_number']} is overdue since {invoice_candidate['due_date'].isoformat()}."
            if reminder_type == "overdue"
            else (
                f"Invoice {invoice_candidate['invoice_number']} is due on {invoice_candidate['due_date'].isoformat()} "
                f"(in {(invoice_candidate['due_date'] - today).days} day(s))."
            )
        )
        event = await crud.create_invoice_reminder_event(
            db,
            invoice_id=invoice_candidate["id"],
            user_id=user_id,
            reminder_type=reminder_type,
            channel="in_app",
            status="sent",
            message=message,
            sent_at=now,
        )
        reminders.append(_to_reminder_event(event))

        if SELF_EMPLOYED_REMINDER_EMAIL_ENABLED:
            email_status, email_message = await _dispatch_invoice_reminder_email(
                invoice_id=invoice_candidate["id"],
                invoice_number=invoice_candidate["invoice_number"],
                reminder_type=reminder_type,
                message=message,
                recipient_email=invoice_candidate["customer_email"],
            )
            email_event = await crud.create_invoice_reminder_event(
                db,
                invoice_id=invoice_candidate["id"],
                user_id=user_id,
                reminder_type=reminder_type,
                channel="email",
                status=email_status,
                message=email_message,
                sent_at=now if email_status == "sent" else None,
            )
            reminders.append(_to_reminder_event(email_event))

        if SELF_EMPLOYED_REMINDER_SMS_ENABLED:
            sms_status, sms_message = await _dispatch_invoice_reminder_sms(
                invoice_id=invoice_candidate["id"],
                invoice_number=invoice_candidate["invoice_number"],
                reminder_type=reminder_type,
                message=message,
                recipient_phone=invoice_candidate["customer_phone"],
            )
            sms_event = await crud.create_invoice_reminder_event(
                db,
                invoice_id=invoice_candidate["id"],
                user_id=user_id,
                reminder_type=reminder_type,
                channel="sms",
                status=sms_status,
                message=sms_message,
                sent_at=now if sms_status == "sent" else None,
            )
            reminders.append(_to_reminder_event(sms_event))

        invoice_to_update = await crud.get_self_employed_invoice_by_id_for_user(
            db,
            invoice_id=invoice_candidate["id"],
            user_id=user_id,
        )
        if invoice_to_update is None:
            continue
        await crud.mark_self_employed_invoice_reminder_sent(
            db,
            invoice_to_update,
            reminder_at=now,
        )

    if reminders:
        sent_by_channel = {
            "in_app": len([item for item in reminders if item.channel == "in_app" and item.status == "sent"]),
            "email": len([item for item in reminders if item.channel == "email" and item.status == "sent"]),
            "sms": len([item for item in reminders if item.channel == "sms" and item.status == "sent"]),
        }
        await log_audit_event(
            user_id=user_id,
            action="self_employed.invoice.reminders.sent",
            details={
                "count": len(reminders),
                "due_in_days": due_in_days,
                "sent_by_channel": sent_by_channel,
            },
        )
    return schemas.SelfEmployedInvoiceReminderRunResponse(
        reminders_sent_count=len(reminders),
        reminders=reminders,
        note="Reminders generated for due-soon/overdue invoices.",
    )


@app.get(
    "/self-employed/invoicing/reminders",
    response_model=schemas.SelfEmployedInvoiceReminderListResponse,
)
async def list_self_employed_invoice_reminders(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total, rows = await crud.list_invoice_reminder_events_for_user(
        db,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return schemas.SelfEmployedInvoiceReminderListResponse(
        total=total,
        items=[_to_reminder_event(item) for item in rows],
    )


@app.post(
    "/self-employed/calendar/events",
    response_model=schemas.SelfEmployedCalendarEvent,
    status_code=status.HTTP_201_CREATED,
)
async def create_self_employed_calendar_event(
    payload: schemas.SelfEmployedCalendarEventCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title cannot be empty")

    starts_at = _to_utc_datetime(payload.starts_at)
    ends_at = _to_utc_datetime(payload.ends_at) if payload.ends_at else None
    if ends_at and ends_at < starts_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ends_at cannot be earlier than starts_at")

    category = (payload.category or "general").strip() or "general"
    description = payload.description.strip() if payload.description else None
    recipient_name = payload.recipient_name.strip() if payload.recipient_name else None
    recipient_email = payload.recipient_email.strip() if payload.recipient_email else None
    recipient_phone = payload.recipient_phone.strip() if payload.recipient_phone else None
    _validate_calendar_notification_channels(
        notify_in_app=payload.notify_in_app,
        notify_email=payload.notify_email,
        notify_sms=payload.notify_sms,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
    )

    event = await crud.create_calendar_event(
        db,
        user_id=user_id,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        description=description,
        category=category,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
        notify_in_app=payload.notify_in_app,
        notify_email=payload.notify_email,
        notify_sms=payload.notify_sms,
        notify_before_minutes=payload.notify_before_minutes,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.calendar.event.created",
        details={
            "event_id": str(event.id),
            "title": event.title,
            "starts_at": _to_utc_datetime(event.starts_at).isoformat(),
            "channels": {
                "in_app": bool(event.notify_in_app),
                "email": bool(event.notify_email),
                "sms": bool(event.notify_sms),
            },
        },
    )
    return _to_calendar_event(event)


@app.get(
    "/self-employed/calendar/events",
    response_model=schemas.SelfEmployedCalendarEventListResponse,
)
async def list_self_employed_calendar_events(
    status_filter: Optional[schemas.SelfEmployedCalendarEventStatus] = Query(default=None, alias="status"),
    start_at: Optional[datetime.datetime] = Query(default=None),
    end_before: Optional[datetime.datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    normalized_start_at = _to_utc_datetime(start_at) if start_at else None
    normalized_end_before = _to_utc_datetime(end_before) if end_before else None
    if normalized_start_at and normalized_end_before and normalized_start_at > normalized_end_before:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_at cannot be after end_before")

    total, rows = await crud.list_calendar_events_for_user(
        db,
        user_id=user_id,
        status=status_filter.value if status_filter else None,
        start_at=normalized_start_at,
        end_before=normalized_end_before,
        limit=limit,
        offset=offset,
    )
    return schemas.SelfEmployedCalendarEventListResponse(
        total=total,
        items=[_to_calendar_event(item) for item in rows],
    )


@app.patch(
    "/self-employed/calendar/events/{event_id}",
    response_model=schemas.SelfEmployedCalendarEvent,
)
async def update_self_employed_calendar_event(
    event_id: uuid.UUID,
    payload: schemas.SelfEmployedCalendarEventUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    event = await crud.get_calendar_event_by_id_for_user(
        db,
        event_id=str(event_id),
        user_id=user_id,
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates:
        if updates["title"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title cannot be null")
        normalized_title = str(updates["title"]).strip()
        if not normalized_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title cannot be empty")
        updates["title"] = normalized_title
    if "description" in updates:
        updates["description"] = str(updates["description"]).strip() if updates["description"] else None
    if "category" in updates:
        category_raw = str(updates["category"]).strip() if updates["category"] else ""
        updates["category"] = category_raw or "general"
    if "recipient_name" in updates:
        updates["recipient_name"] = str(updates["recipient_name"]).strip() if updates["recipient_name"] else None
    if "recipient_email" in updates:
        updates["recipient_email"] = str(updates["recipient_email"]).strip() if updates["recipient_email"] else None
    if "recipient_phone" in updates:
        updates["recipient_phone"] = str(updates["recipient_phone"]).strip() if updates["recipient_phone"] else None
    if "starts_at" in updates:
        if updates["starts_at"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="starts_at cannot be null")
        updates["starts_at"] = _to_utc_datetime(updates["starts_at"])
    if "ends_at" in updates and updates["ends_at"] is not None:
        updates["ends_at"] = _to_utc_datetime(updates["ends_at"])
    if "notify_before_minutes" in updates and updates["notify_before_minutes"] is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="notify_before_minutes cannot be null")
    if "status" in updates:
        if updates["status"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status cannot be null")
        updates["status"] = updates["status"].value if hasattr(updates["status"], "value") else str(updates["status"])

    effective_starts_at = updates.get("starts_at", _to_utc_datetime(event.starts_at))
    effective_ends_at = updates.get("ends_at", _to_utc_datetime(event.ends_at) if event.ends_at else None)
    if effective_ends_at and effective_ends_at < effective_starts_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ends_at cannot be earlier than starts_at")

    notify_in_app = bool(updates.get("notify_in_app", event.notify_in_app))
    notify_email = bool(updates.get("notify_email", event.notify_email))
    notify_sms = bool(updates.get("notify_sms", event.notify_sms))
    recipient_email = updates.get("recipient_email", event.recipient_email)
    recipient_phone = updates.get("recipient_phone", event.recipient_phone)
    _validate_calendar_notification_channels(
        notify_in_app=notify_in_app,
        notify_email=notify_email,
        notify_sms=notify_sms,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
    )

    updated = await crud.update_calendar_event(
        db,
        event,
        updates=updates,
    )
    await log_audit_event(
        user_id=user_id,
        action="self_employed.calendar.event.updated",
        details={
            "event_id": str(event_id),
            "updated_fields": sorted(list(updates.keys())),
        },
    )
    return _to_calendar_event(updated)


@app.delete(
    "/self-employed/calendar/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_self_employed_calendar_event(
    event_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    event = await crud.get_calendar_event_by_id_for_user(
        db,
        event_id=str(event_id),
        user_id=user_id,
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found")
    await crud.delete_calendar_event(db, event)
    await log_audit_event(
        user_id=user_id,
        action="self_employed.calendar.event.deleted",
        details={"event_id": str(event_id), "title": event.title},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _run_calendar_reminders_for_user(
    db: AsyncSession,
    *,
    user_id: str,
    horizon_hours: int,
    source: Literal["manual", "scheduler"] = "manual",
) -> schemas.SelfEmployedCalendarReminderRunResponse:
    now = datetime.datetime.now(datetime.UTC)
    horizon_end = now + datetime.timedelta(hours=horizon_hours)
    rows = await crud.list_calendar_events_due_for_reminders(
        db,
        user_id=user_id,
        horizon_end=horizon_end,
        limit=500,
    )
    event_candidates = [
        {
            "id": str(item.id),
            "title": str(item.title),
            "starts_at": _to_utc_datetime(item.starts_at),
            "notify_before_minutes": int(item.notify_before_minutes or 0),
            "notify_in_app": bool(item.notify_in_app),
            "notify_email": bool(item.notify_email),
            "notify_sms": bool(item.notify_sms),
            "recipient_email": item.recipient_email,
            "recipient_phone": item.recipient_phone,
            "reminder_last_sent_at": _to_utc_datetime(item.reminder_last_sent_at) if item.reminder_last_sent_at else None,
        }
        for item in rows
    ]

    reminders: list[schemas.SelfEmployedCalendarReminderEvent] = []
    cooldown_seconds = SELF_EMPLOYED_CALENDAR_REMINDER_COOLDOWN_HOURS * 3600
    for event_candidate in event_candidates:
        starts_at = event_candidate["starts_at"]
        reminder_window_start = starts_at - datetime.timedelta(minutes=max(event_candidate["notify_before_minutes"], 0))
        if now < reminder_window_start:
            continue
        if event_candidate["reminder_last_sent_at"] and (
            now - event_candidate["reminder_last_sent_at"]
        ).total_seconds() < cooldown_seconds:
            continue

        reminder_type: Literal["upcoming", "overdue"] = "overdue" if starts_at < now else "upcoming"
        minutes_delta = int(max((starts_at - now).total_seconds(), 0) // 60)
        message = (
            f"Calendar event '{event_candidate['title']}' was scheduled for {starts_at.isoformat()} and needs attention."
            if reminder_type == "overdue"
            else (
                f"Calendar event '{event_candidate['title']}' starts at {starts_at.isoformat()} "
                f"(in {minutes_delta} minute(s))."
            )
        )

        sent_any = False
        if event_candidate["notify_in_app"]:
            in_app_event = await crud.create_calendar_reminder_event(
                db,
                event_id=event_candidate["id"],
                user_id=user_id,
                reminder_type=reminder_type,
                channel="in_app",
                status="sent",
                message=message,
                sent_at=now,
            )
            reminders.append(_to_calendar_reminder_event(in_app_event))
            sent_any = True

        if event_candidate["notify_email"]:
            email_status, email_message = await _dispatch_calendar_reminder_email(
                event_id=event_candidate["id"],
                title=event_candidate["title"],
                starts_at=starts_at,
                reminder_type=reminder_type,
                message=message,
                recipient_email=event_candidate["recipient_email"],
            )
            email_event = await crud.create_calendar_reminder_event(
                db,
                event_id=event_candidate["id"],
                user_id=user_id,
                reminder_type=reminder_type,
                channel="email",
                status=email_status,
                message=email_message,
                sent_at=now if email_status == "sent" else None,
            )
            reminders.append(_to_calendar_reminder_event(email_event))
            sent_any = sent_any or email_status == "sent"

        if event_candidate["notify_sms"]:
            sms_status, sms_message = await _dispatch_calendar_reminder_sms(
                event_id=event_candidate["id"],
                title=event_candidate["title"],
                starts_at=starts_at,
                reminder_type=reminder_type,
                message=message,
                recipient_phone=event_candidate["recipient_phone"],
            )
            sms_event = await crud.create_calendar_reminder_event(
                db,
                event_id=event_candidate["id"],
                user_id=user_id,
                reminder_type=reminder_type,
                channel="sms",
                status=sms_status,
                message=sms_message,
                sent_at=now if sms_status == "sent" else None,
            )
            reminders.append(_to_calendar_reminder_event(sms_event))
            sent_any = sent_any or sms_status == "sent"

        if sent_any:
            event_to_update = await crud.get_calendar_event_by_id_for_user(
                db,
                event_id=event_candidate["id"],
                user_id=user_id,
            )
            if event_to_update:
                await crud.mark_calendar_event_reminder_sent(
                    db,
                    event_to_update,
                    reminder_at=now,
                )

    if reminders:
        sent_by_channel = {
            "in_app": len([item for item in reminders if item.channel == "in_app" and item.status == "sent"]),
            "email": len([item for item in reminders if item.channel == "email" and item.status == "sent"]),
            "sms": len([item for item in reminders if item.channel == "sms" and item.status == "sent"]),
        }
        await log_audit_event(
            user_id=user_id,
            action="self_employed.calendar.reminders.sent",
            details={
                "count": len(reminders),
                "horizon_hours": horizon_hours,
                "sent_by_channel": sent_by_channel,
                "source": source,
            },
        )
    note = "No calendar reminders due." if not reminders else "Calendar reminders generated for events in window."
    return schemas.SelfEmployedCalendarReminderRunResponse(
        reminders_sent_count=len(reminders),
        reminders=reminders,
        note=note,
    )


@app.post(
    "/self-employed/calendar/reminders/run",
    response_model=schemas.SelfEmployedCalendarReminderRunResponse,
)
async def run_self_employed_calendar_reminders(
    horizon_hours: int = Query(default=48, ge=1, le=336),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await _run_calendar_reminders_for_user(
        db,
        user_id=user_id,
        horizon_hours=horizon_hours,
        source="manual",
    )


@app.get(
    "/self-employed/calendar/reminders",
    response_model=schemas.SelfEmployedCalendarReminderListResponse,
)
async def list_self_employed_calendar_reminders(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total, rows = await crud.list_calendar_reminder_events_for_user(
        db,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return schemas.SelfEmployedCalendarReminderListResponse(
        total=total,
        items=[_to_calendar_reminder_event(item) for item in rows],
    )


@app.post(
    "/billing/invoices/generate",
    response_model=schemas.BillingInvoiceDetail,
    status_code=status.HTTP_201_CREATED,
)
async def generate_billing_invoice(
    payload: schemas.BillingInvoiceGenerateRequest,
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    invoice_statuses = _resolve_billing_statuses(payload.statuses)
    report = await _load_billing_report(
        db=db,
        partner_id=payload.partner_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        statuses=invoice_statuses,
    )
    invoice = await crud.create_billing_invoice(
        db,
        generated_by_user_id=user_id,
        partner_id=str(payload.partner_id) if payload.partner_id else None,
        period_start=payload.start_date,
        period_end=payload.end_date,
        statuses=invoice_statuses,
        currency=report.currency,
        total_amount_gbp=report.total_amount_gbp,
        due_days=BILLING_INVOICE_DUE_DAYS,
        lines=[
            {
                "partner_id": str(item.partner_id),
                "partner_name": item.partner_name,
                "qualified_leads": item.qualified_leads,
                "converted_leads": item.converted_leads,
                "unique_users": item.unique_users,
                "qualified_lead_fee_gbp": item.qualified_lead_fee_gbp,
                "converted_lead_fee_gbp": item.converted_lead_fee_gbp,
                "amount_gbp": item.amount_gbp,
            }
            for item in report.by_partner
        ],
    )

    await log_audit_event(
        user_id=user_id,
        action="partner.billing.invoice.generated",
        details={
            "invoice_id": str(invoice.id),
            "total_amount_gbp": report.total_amount_gbp,
            "currency": report.currency,
            "lines_count": len(report.by_partner),
        },
    )

    return await _load_invoice_detail(db, uuid.UUID(str(invoice.id)))


@app.get("/billing/invoices", response_model=schemas.BillingInvoiceListResponse)
async def list_billing_invoices(
    invoice_status: Optional[schemas.BillingInvoiceStatus] = Query(default=None, alias="status"),
    partner_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    total, invoices = await crud.list_billing_invoices(
        db,
        status=invoice_status.value if invoice_status else None,
        partner_id=str(partner_id) if partner_id else None,
        limit=limit,
        offset=offset,
    )
    return schemas.BillingInvoiceListResponse(
        total=total,
        items=[_to_invoice_summary(invoice) for invoice in invoices],
    )


@app.get("/billing/invoices/{invoice_id}", response_model=schemas.BillingInvoiceDetail)
async def get_billing_invoice(
    invoice_id: uuid.UUID,
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    return await _load_invoice_detail(db, invoice_id=invoice_id)


@app.get("/billing/invoices/{invoice_id}/pdf")
async def download_billing_invoice_pdf(
    invoice_id: uuid.UUID,
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    invoice = await _load_invoice_detail(db, invoice_id=invoice_id)
    await log_audit_event(
        user_id=user_id,
        action="partner.billing.invoice.pdf_downloaded",
        details={"invoice_id": str(invoice_id), "invoice_number": invoice.invoice_number},
    )
    return _invoice_pdf_response(invoice)


@app.get("/billing/invoices/{invoice_id}/accounting.csv")
async def download_billing_invoice_accounting_csv(
    invoice_id: uuid.UUID,
    target: Literal["xero", "quickbooks"] = Query(default="xero"),
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    invoice = await _load_invoice_detail(db, invoice_id=invoice_id)
    await log_audit_event(
        user_id=user_id,
        action="partner.billing.invoice.accounting_exported",
        details={
            "invoice_id": str(invoice_id),
            "invoice_number": invoice.invoice_number,
            "target": target,
        },
    )
    return _accounting_csv_response(invoice, target=target)


@app.patch("/billing/invoices/{invoice_id}/status", response_model=schemas.BillingInvoiceDetail)
async def update_billing_invoice_status(
    invoice_id: uuid.UUID,
    payload: schemas.BillingInvoiceStatusUpdateRequest,
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    invoice = await crud.get_billing_invoice_by_id(db, str(invoice_id))
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    _validate_invoice_status_transition(invoice.status, payload.status)
    previous_status = invoice.status
    if payload.status.value != invoice.status:
        invoice = await crud.update_billing_invoice_status(db, invoice, status=payload.status.value)
        await log_audit_event(
            user_id=user_id,
            action="partner.billing.invoice.status.updated",
            details={
                "invoice_id": str(invoice.id),
                "from_status": previous_status,
                "to_status": payload.status.value,
            },
        )

    return await _load_invoice_detail(db, invoice_id=invoice_id)


@app.get("/leads/billing", response_model=schemas.BillingReportResponse)
async def get_lead_billing_report(
    report_format: Literal["json", "csv"] = Query(default="json", alias="format"),
    partner_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    statuses: Optional[List[schemas.LeadStatus]] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    report = await _load_billing_report(
        db=db,
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date,
        statuses=_resolve_billing_statuses(statuses),
    )
    if report_format == "csv":
        return _billing_csv_response(report)
    return report


@app.get("/leads/funnel-summary", response_model=schemas.LeadFunnelSummaryResponse)
async def get_lead_funnel_summary(
    partner_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    report = await _load_billing_report(
        db=db,
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date,
        statuses=[],
    )
    total_leads = report.total_leads
    qualified_leads = report.qualified_leads
    converted_leads = report.converted_leads
    qualification_rate = round((qualified_leads / total_leads) * 100, 1) if total_leads else 0.0
    conversion_from_qualified = round((converted_leads / qualified_leads) * 100, 1) if qualified_leads else 0.0
    overall_conversion = round((converted_leads / total_leads) * 100, 1) if total_leads else 0.0
    return schemas.LeadFunnelSummaryResponse(
        period_start=report.period_start,
        period_end=report.period_end,
        total_leads=total_leads,
        qualified_leads=qualified_leads,
        converted_leads=converted_leads,
        qualification_rate_percent=qualification_rate,
        conversion_rate_from_qualified_percent=conversion_from_qualified,
        overall_conversion_rate_percent=overall_conversion,
    )


@app.post(
    "/investor/marketing-spend",
    response_model=schemas.MarketingSpendIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_marketing_spend(
    payload: schemas.MarketingSpendIngestRequest,
    user_id: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    channel = payload.channel.strip().lower()
    if not channel:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="channel cannot be empty")
    record = models.MarketingSpendEntry(
        month_start=_month_start(payload.month_start),
        channel=channel,
        spend_gbp=payload.spend_gbp,
        acquired_customers=payload.acquired_customers,
        created_by_user_id=user_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    await log_audit_event(
        user_id=user_id,
        action="investor.marketing_spend.ingested",
        details={
            "entry_id": str(record.id),
            "month_start": record.month_start.isoformat(),
            "channel": record.channel,
            "spend_gbp": record.spend_gbp,
            "acquired_customers": record.acquired_customers,
        },
    )
    return schemas.MarketingSpendIngestResponse(
        entry_id=uuid.UUID(str(record.id)),
        month_start=record.month_start,
        channel=record.channel,
        spend_gbp=record.spend_gbp,
        acquired_customers=record.acquired_customers,
        created_at=record.created_at,
        message="Marketing spend entry recorded successfully.",
    )


@app.post(
    "/investor/nps/responses",
    response_model=schemas.NPSSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_nps_response(
    payload: schemas.NPSSubmissionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    feedback = payload.feedback.strip() if payload.feedback else None
    context_tag = payload.context_tag.strip() if payload.context_tag else None
    locale = payload.locale.strip() if payload.locale else None
    record = models.NPSResponse(
        user_id=user_id,
        score=payload.score,
        feedback=feedback,
        context_tag=context_tag,
        locale=locale,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    await log_audit_event(
        user_id=user_id,
        action="investor.nps.submitted",
        details={
            "response_id": str(record.id),
            "score": payload.score,
            "score_band": _nps_score_band(payload.score),
            "context_tag": context_tag,
        },
    )
    return schemas.NPSSubmissionResponse(
        response_id=uuid.UUID(str(record.id)),
        score_band=_nps_score_band(payload.score),
        submitted_at=record.created_at,
        message="NPS feedback submitted. Thank you for helping improve product quality.",
    )


@app.get("/investor/nps/trend", response_model=schemas.NPSTrendResponse)
async def get_nps_trend(
    period_months: int = Query(default=6, ge=NPS_MIN_PERIOD_MONTHS, le=NPS_MAX_PERIOD_MONTHS),
    as_of_date: Optional[datetime.date] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    effective_as_of_date = as_of_date or datetime.datetime.now(datetime.UTC).date()
    trend = await _load_nps_trend(
        db,
        as_of_date=effective_as_of_date,
        period_months=period_months,
    )
    return _build_nps_trend_response(period_months=period_months, trend=trend)


@app.get("/investor/seed-readiness", response_model=schemas.SeedReadinessResponse)
async def get_seed_readiness_snapshot(
    period_months: int = Query(default=6, ge=SEED_READINESS_MIN_PERIOD_MONTHS, le=SEED_READINESS_MAX_PERIOD_MONTHS),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    as_of_date = datetime.datetime.now(datetime.UTC).date()
    return await _build_seed_readiness_snapshot(
        db,
        period_months=period_months,
        as_of_date=as_of_date,
    )


@app.get("/investor/unit-economics", response_model=schemas.UnitEconomicsResponse)
async def get_unit_economics_snapshot(
    period_months: int = Query(
        default=6,
        ge=UNIT_ECONOMICS_MIN_PERIOD_MONTHS,
        le=UNIT_ECONOMICS_MAX_PERIOD_MONTHS,
    ),
    as_of_date: Optional[datetime.date] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    effective_as_of_date = as_of_date or datetime.datetime.now(datetime.UTC).date()
    return await _build_unit_economics_snapshot(
        db,
        period_months=period_months,
        as_of_date=effective_as_of_date,
    )


@app.get("/investor/pmf-evidence", response_model=schemas.PMFEvidenceResponse)
async def get_pmf_evidence_snapshot(
    cohort_months: int = Query(default=6, ge=PMF_MIN_COHORT_MONTHS, le=PMF_MAX_COHORT_MONTHS),
    activation_window_days: int = Query(
        default=30,
        ge=PMF_MIN_ACTIVATION_WINDOW_DAYS,
        le=PMF_MAX_ACTIVATION_WINDOW_DAYS,
    ),
    as_of_date: Optional[datetime.date] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    effective_as_of_date = as_of_date or datetime.datetime.now(datetime.UTC).date()
    return await _build_pmf_evidence_snapshot(
        db,
        cohort_months=cohort_months,
        activation_window_days=activation_window_days,
        as_of_date=effective_as_of_date,
    )


@app.get("/investor/pmf-gate", response_model=schemas.PMFGateStatusResponse)
async def get_pmf_gate_status(
    cohort_months: int = Query(default=6, ge=PMF_MIN_COHORT_MONTHS, le=PMF_MAX_COHORT_MONTHS),
    activation_window_days: int = Query(
        default=30,
        ge=PMF_MIN_ACTIVATION_WINDOW_DAYS,
        le=PMF_MAX_ACTIVATION_WINDOW_DAYS,
    ),
    nps_period_months: int = Query(default=6, ge=NPS_MIN_PERIOD_MONTHS, le=NPS_MAX_PERIOD_MONTHS),
    as_of_date: Optional[datetime.date] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    effective_as_of_date = as_of_date or datetime.datetime.now(datetime.UTC).date()
    pmf_evidence = await _build_pmf_evidence_snapshot(
        db,
        cohort_months=cohort_months,
        activation_window_days=activation_window_days,
        as_of_date=effective_as_of_date,
    )
    nps_trend_data = await _load_nps_trend(
        db,
        as_of_date=effective_as_of_date,
        period_months=nps_period_months,
    )
    nps_trend = _build_nps_trend_response(period_months=nps_period_months, trend=nps_trend_data)
    return _build_pmf_gate_status(pmf_evidence=pmf_evidence, nps_trend=nps_trend)


@app.get("/investor/snapshot/export", response_model=schemas.InvestorSnapshotExportResponse)
async def export_investor_snapshot(
    report_format: Literal["json", "csv"] = Query(default="json", alias="format"),
    seed_period_months: int = Query(default=6, ge=SEED_READINESS_MIN_PERIOD_MONTHS, le=SEED_READINESS_MAX_PERIOD_MONTHS),
    unit_econ_period_months: int = Query(
        default=6,
        ge=UNIT_ECONOMICS_MIN_PERIOD_MONTHS,
        le=UNIT_ECONOMICS_MAX_PERIOD_MONTHS,
    ),
    cohort_months: int = Query(default=6, ge=PMF_MIN_COHORT_MONTHS, le=PMF_MAX_COHORT_MONTHS),
    activation_window_days: int = Query(
        default=30,
        ge=PMF_MIN_ACTIVATION_WINDOW_DAYS,
        le=PMF_MAX_ACTIVATION_WINDOW_DAYS,
    ),
    nps_period_months: int = Query(default=6, ge=NPS_MIN_PERIOD_MONTHS, le=NPS_MAX_PERIOD_MONTHS),
    as_of_date: Optional[datetime.date] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    effective_as_of_date = as_of_date or datetime.datetime.now(datetime.UTC).date()
    seed_snapshot = await _build_seed_readiness_snapshot(
        db,
        period_months=seed_period_months,
        as_of_date=effective_as_of_date,
    )
    pmf_evidence = await _build_pmf_evidence_snapshot(
        db,
        cohort_months=cohort_months,
        activation_window_days=activation_window_days,
        as_of_date=effective_as_of_date,
    )
    nps_trend_data = await _load_nps_trend(
        db,
        as_of_date=effective_as_of_date,
        period_months=nps_period_months,
    )
    nps_trend = _build_nps_trend_response(period_months=nps_period_months, trend=nps_trend_data)
    pmf_gate = _build_pmf_gate_status(pmf_evidence=pmf_evidence, nps_trend=nps_trend)
    unit_economics = await _build_unit_economics_snapshot(
        db,
        period_months=unit_econ_period_months,
        as_of_date=effective_as_of_date,
    )
    snapshot = schemas.InvestorSnapshotExportResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        as_of_date=effective_as_of_date,
        seed_readiness=seed_snapshot,
        pmf_evidence=pmf_evidence,
        nps_trend=nps_trend,
        pmf_gate=pmf_gate,
        unit_economics=unit_economics,
    )
    if report_format == "csv":
        return Response(
            content=_build_investor_snapshot_csv(snapshot),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="investor_snapshot.csv"'},
        )
    return snapshot


@app.get("/leads/billing.csv")
async def export_lead_billing_csv(
    partner_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    statuses: Optional[List[schemas.LeadStatus]] = Query(default=None),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    report = await _load_billing_report(
        db=db,
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date,
        statuses=_resolve_billing_statuses(statuses),
    )
    return _billing_csv_response(report)


@app.get("/leads/report", response_model=schemas.LeadReportResponse)
async def get_lead_report(
    report_format: Literal["json", "csv"] = Query(default="json", alias="format"),
    partner_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    statuses: Optional[List[schemas.LeadStatus]] = Query(default=None),
    billable_only: bool = Query(default=True),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    report_statuses = _resolve_report_statuses(billable_only=billable_only, statuses=statuses)
    report = await _load_lead_report(
        db=db,
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date,
        statuses=report_statuses,
    )
    if report_format == "csv":
        return _csv_response(report)
    return report


@app.get("/leads/report.csv")
async def export_lead_report_csv(
    partner_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    statuses: Optional[List[schemas.LeadStatus]] = Query(default=None),
    billable_only: bool = Query(default=True),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    report_statuses = _resolve_report_statuses(billable_only=billable_only, statuses=statuses)
    report = await _load_lead_report(
        db=db,
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date,
        statuses=report_statuses,
    )
    return _csv_response(report)

