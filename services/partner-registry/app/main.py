import datetime
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, schemas
from .database import AsyncSessionLocal, Base, engine, get_db

COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_http.retry import post_json_with_retry

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
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

    existing_lead = await crud.get_recent_handoff_lead(
        db,
        user_id=user_id,
        partner_id=partner_db_id,
    )
    if existing_lead:
        return schemas.HandoffResponse(
            message=f"Handoff to {partner_name} already initiated recently.",
            lead_id=uuid.UUID(str(existing_lead.id)),
            duplicated=True,
        )

    lead = await crud.create_handoff_lead(
        db,
        user_id=user_id,
        partner_id=partner_db_id,
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


@app.get("/leads/report", response_model=schemas.LeadReportResponse)
async def get_lead_report(
    partner_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    _user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
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

    total_leads, unique_users, by_partner_rows = await crud.get_lead_report(
        db,
        partner_id=str(partner_id) if partner_id else None,
        start_at=start_at,
        end_before=end_before,
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

