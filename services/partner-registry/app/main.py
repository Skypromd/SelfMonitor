import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import Base, engine, get_db

COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Partner Registry Service",
    description="Manages a registry of third-party partners.",
    version="1.0.0",
)


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async for db in get_db():
        await crud.seed_partners_if_empty(db)
        break


async def log_audit_event(user_id: str, action: str, details: Dict[str, Any]) -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                COMPLIANCE_SERVICE_URL,
                json={"user_id": user_id, "action": action, "details": details},
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json().get("id")
    except httpx.RequestError as exc:
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


@app.post("/partners/{partner_id}/handoff", status_code=status.HTTP_202_ACCEPTED)
async def initiate_handoff(
    partner_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    partner = await crud.get_partner_by_id(db, str(partner_id))
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    audit_event_id = await log_audit_event(
        user_id=user_id,
        action="partner.handoff.initiated",
        details={
            "partner_id": str(partner.id),
            "partner_name": partner.name,
        },
    )

    return {
        "message": f"Handoff to {partner.name} initiated.",
        "audit_event_id": audit_event_id,
    }

