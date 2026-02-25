import datetime
import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models, schemas


async def create_consent(db: AsyncSession, user_id: str, consent_in: schemas.ConsentCreate) -> models.Consent:
    db_consent = models.Consent(
        user_id=user_id,
        connection_id=str(consent_in.connection_id),
        provider=consent_in.provider,
        scopes=consent_in.scopes,
        status="active",
    )
    db.add(db_consent)
    await db.commit()
    await db.refresh(db_consent)
    return db_consent


async def list_active_consents(db: AsyncSession, user_id: str) -> List[models.Consent]:
    result = await db.execute(
        select(models.Consent)
        .filter(models.Consent.user_id == user_id, models.Consent.status == "active")
        .order_by(models.Consent.created_at.desc())
    )
    return result.scalars().all()


async def get_consent_by_id(db: AsyncSession, user_id: str, consent_id: uuid.UUID) -> models.Consent | None:
    result = await db.execute(
        select(models.Consent).filter(
            models.Consent.id == str(consent_id),
            models.Consent.user_id == user_id,
        )
    )
    return result.scalars().first()


async def revoke_consent(db: AsyncSession, consent: models.Consent) -> models.Consent:
    consent.status = "revoked"
    consent.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(consent)
    return consent

