"""User-owned businesses (multi-business / Business tier)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models

DEFAULT_BUSINESS_NAMESPACE = uuid.UUID("018f0d8e-7f3a-7b3d-9c2a-1e2f3a4b6d7d")
MAX_BUSINESSES_BUSINESS_PLAN = 10


def default_business_uuid(user_id: str) -> uuid.UUID:
    return uuid.uuid5(DEFAULT_BUSINESS_NAMESPACE, user_id)


async def ensure_default_business(db: AsyncSession, user_id: str, default_id: uuid.UUID) -> None:
    existing = await db.execute(
        select(models.UserBusiness).filter(models.UserBusiness.id == default_id)
    )
    if existing.scalars().first():
        return
    db.add(
        models.UserBusiness(
            id=default_id,
            user_id=user_id,
            display_name="Primary",
        )
    )
    await db.commit()


async def user_owns_business(db: AsyncSession, user_id: str, business_id: uuid.UUID) -> bool:
    r = await db.execute(
        select(models.UserBusiness).filter(
            models.UserBusiness.id == business_id,
            models.UserBusiness.user_id == user_id,
        )
    )
    return r.scalars().first() is not None


async def list_businesses(db: AsyncSession, user_id: str) -> list[models.UserBusiness]:
    r = await db.execute(
        select(models.UserBusiness)
        .filter(models.UserBusiness.user_id == user_id)
        .order_by(models.UserBusiness.display_name.asc())
    )
    return list(r.scalars().all())


async def count_businesses(db: AsyncSession, user_id: str) -> int:
    r = await db.execute(
        select(func.count())
        .select_from(models.UserBusiness)
        .filter(models.UserBusiness.user_id == user_id)
    )
    return int(r.scalar_one() or 0)


async def create_business(
    db: AsyncSession,
    *,
    user_id: str,
    display_name: str,
) -> models.UserBusiness:
    row = models.UserBusiness(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name=display_name.strip()[:120] or "Business",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def rename_business(
    db: AsyncSession,
    *,
    user_id: str,
    business_id: uuid.UUID,
    display_name: str,
) -> models.UserBusiness | None:
    r = await db.execute(
        select(models.UserBusiness).filter(
            models.UserBusiness.id == business_id,
            models.UserBusiness.user_id == user_id,
        )
    )
    row = r.scalars().first()
    if not row:
        return None
    row.display_name = display_name.strip()[:120] or row.display_name
    await db.commit()
    await db.refresh(row)
    return row
