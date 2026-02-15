import datetime
import csv
import io
import os
import sys
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
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


BILLING_INVOICE_DUE_DAYS = _parse_positive_int_env("BILLING_INVOICE_DUE_DAYS", 14)
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

SEED_READINESS_MIN_PERIOD_MONTHS = 3
SEED_READINESS_MAX_PERIOD_MONTHS = 24
PMF_MIN_COHORT_MONTHS = 3
PMF_MAX_COHORT_MONTHS = 24
PMF_MIN_ACTIVATION_WINDOW_DAYS = 7
PMF_MAX_ACTIVATION_WINDOW_DAYS = 60


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
    yield


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


@app.get("/investor/seed-readiness", response_model=schemas.SeedReadinessResponse)
async def get_seed_readiness_snapshot(
    period_months: int = Query(default=6, ge=SEED_READINESS_MIN_PERIOD_MONTHS, le=SEED_READINESS_MAX_PERIOD_MONTHS),
    _billing_user: str = Depends(require_billing_report_access),
    db: AsyncSession = Depends(get_db),
):
    as_of_date = datetime.datetime.now(datetime.UTC).date()
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
    cohort_start = _shift_month(_month_start(effective_as_of_date), -(cohort_months - 1))
    activity_by_user = await _load_pmf_user_activity(
        db,
        cohort_start=cohort_start,
        as_of_date=effective_as_of_date,
    )
    pmf_rows = _build_user_pmf_flags(
        activity_by_user=activity_by_user,
        as_of_date=effective_as_of_date,
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
        as_of_date=effective_as_of_date,
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

