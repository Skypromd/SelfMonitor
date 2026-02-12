import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

import httpx
from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, schemas
from .database import Base, engine, get_db

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
    yield


app = FastAPI(
    title="Consent Service",
    description="Manages user consents for data access.",
    version="1.0.0",
    lifespan=lifespan,
)


async def log_audit_event(user_id: str, action: str, details: Dict[str, Any]):
    try:
        await post_json_with_retry(
            COMPLIANCE_SERVICE_URL,
            json_body={"user_id": user_id, "action": action, "details": details},
            timeout=5.0,
            expect_json=False,
        )
    except httpx.HTTPError as exc:
        print(f"Error: Could not log audit event to compliance service: {exc}")


@app.post("/consents", response_model=schemas.Consent, status_code=status.HTTP_201_CREATED)
async def record_consent(
    consent_in: schemas.ConsentCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    new_consent = await crud.create_consent(db, user_id=user_id, consent_in=consent_in)

    await log_audit_event(
        user_id=user_id,
        action="consent.granted",
        details={
            "consent_id": str(new_consent.id),
            "provider": new_consent.provider,
            "scopes": new_consent.scopes,
        },
    )
    return new_consent


@app.get("/consents", response_model=List[schemas.Consent])
async def list_active_consents(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_active_consents(db, user_id=user_id)


@app.get("/consents/{consent_id}", response_model=schemas.Consent)
async def get_consent(
    consent_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    consent = await crud.get_consent_by_id(db, user_id=user_id, consent_id=consent_id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return consent


@app.delete("/consents/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    consent_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    consent = await crud.get_consent_by_id(db, user_id=user_id, consent_id=consent_id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")

    if consent.status != "revoked":
        consent = await crud.revoke_consent(db, consent=consent)
        await log_audit_event(
            user_id=user_id,
            action="consent.revoked",
            details={"consent_id": str(consent.id)},
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

