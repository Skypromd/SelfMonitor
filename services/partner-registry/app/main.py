import datetime
import csv
import io
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from . import crud, schemas
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
LEAD_STATUS_TRANSITIONS = {
    schemas.LeadStatus.initiated.value: {schemas.LeadStatus.qualified.value, schemas.LeadStatus.rejected.value},
    schemas.LeadStatus.qualified.value: {schemas.LeadStatus.converted.value, schemas.LeadStatus.rejected.value},
    schemas.LeadStatus.rejected.value: set(),
    schemas.LeadStatus.converted.value: set(),
}


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


def _resolve_report_statuses(
    billable_only: bool,
    statuses: list[schemas.LeadStatus] | None,
) -> list[str] | None:
    if statuses:
        return [status_item.value for status_item in statuses]
    if billable_only:
        return list(DEFAULT_BILLABLE_STATUSES)
    return None


def _validate_status_transition(current_status: str, target_status: schemas.LeadStatus) -> None:
    if target_status.value == current_status:
        return

    allowed = LEAD_STATUS_TRANSITIONS.get(current_status, set())
    if target_status.value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition lead status from {current_status} to {target_status.value}",
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

