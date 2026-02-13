import datetime
import hashlib
from typing import List, Optional

from sqlalchemy import Select, distinct, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models

SEED_PARTNERS = [
    {
        "id": "1a8a8f69-a1b7-4c13-9a16-9e9f9a2e3f5d",
        "name": "SafeFuture Financial Advisors",
        "description": "Independent financial advisors regulated by the FCA.",
        "services_offered": ["pension_advice", "investment_management", "income_protection"],
        "website": "https://www.safefuture.example.com",
    },
    {
        "id": "b4f1f2d5-9c9a-4e1e-b8d4-5b4d7f6c3a1b",
        "name": "HomePath Mortgages",
        "description": "Specialist mortgage brokers for first-time buyers.",
        "services_offered": ["mortgage_advice"],
        "website": "https://www.homepath.example.com",
    },
    {
        "id": "c5e3e1d4-8d8a-3d0d-a7c3-4c3d6f5b2a0a",
        "name": "TaxSolve Accountants",
        "description": "Chartered accountants specializing in self-assessment for freelancers.",
        "services_offered": ["accounting", "tax_filing"],
        "website": "https://www.taxsolve.example.com",
    },
]


async def seed_partners_if_empty(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(models.Partner))
    partners_count = result.scalar_one()
    if partners_count > 0:
        return

    db.add_all([models.Partner(**partner_data) for partner_data in SEED_PARTNERS])
    await db.commit()


async def list_partners(db: AsyncSession, service_type: Optional[str] = None) -> List[models.Partner]:
    result = await db.execute(select(models.Partner).order_by(models.Partner.name.asc()))
    partners = result.scalars().all()
    if not service_type:
        return partners
    return [partner for partner in partners if service_type in (partner.services_offered or [])]


async def get_partner_by_id(db: AsyncSession, partner_id: str) -> models.Partner | None:
    result = await db.execute(select(models.Partner).filter(models.Partner.id == partner_id))
    return result.scalars().first()


async def get_recent_handoff_lead(
    db: AsyncSession,
    user_id: str,
    partner_id: str,
    dedupe_window_hours: int = 24,
) -> models.HandoffLead | None:
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=dedupe_window_hours)
    result = await db.execute(
        select(models.HandoffLead)
        .filter(
            models.HandoffLead.user_id == user_id,
            models.HandoffLead.partner_id == partner_id,
            models.HandoffLead.created_at >= cutoff,
        )
        .order_by(models.HandoffLead.created_at.desc())
    )
    return result.scalars().first()


async def create_handoff_lead(db: AsyncSession, user_id: str, partner_id: str) -> models.HandoffLead:
    lead = models.HandoffLead(user_id=user_id, partner_id=partner_id, status="initiated")
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


def _dedupe_lock_key(user_id: str, partner_id: str) -> int:
    digest = hashlib.blake2b(f"{user_id}:{partner_id}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) & 0x7FFF_FFFF_FFFF_FFFF


async def _acquire_dedupe_lock_if_postgres(db: AsyncSession, user_id: str, partner_id: str) -> None:
    bind = db.get_bind()
    if not bind or bind.dialect.name != "postgresql":
        return

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _dedupe_lock_key(user_id=user_id, partner_id=partner_id)},
    )


async def create_or_get_handoff_lead(
    db: AsyncSession,
    user_id: str,
    partner_id: str,
    dedupe_window_hours: int = 24,
) -> tuple[models.HandoffLead, bool]:
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=dedupe_window_hours)

    await _acquire_dedupe_lock_if_postgres(db, user_id=user_id, partner_id=partner_id)

    recent_lead_query = (
        select(models.HandoffLead)
        .filter(
            models.HandoffLead.user_id == user_id,
            models.HandoffLead.partner_id == partner_id,
            models.HandoffLead.created_at >= cutoff,
        )
        .order_by(models.HandoffLead.created_at.desc())
    )

    bind = db.get_bind()
    if bind and bind.dialect.name == "postgresql":
        recent_lead_query = recent_lead_query.with_for_update()

    result = await db.execute(recent_lead_query)
    existing_lead = result.scalars().first()
    if existing_lead:
        await db.commit()
        await db.refresh(existing_lead)
        return existing_lead, True

    lead = models.HandoffLead(user_id=user_id, partner_id=partner_id, status="initiated")
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead, False


async def get_handoff_lead_by_id(db: AsyncSession, lead_id: str) -> models.HandoffLead | None:
    result = await db.execute(select(models.HandoffLead).filter(models.HandoffLead.id == lead_id))
    return result.scalars().first()


async def update_handoff_lead_status(
    db: AsyncSession,
    lead: models.HandoffLead,
    status: str,
) -> models.HandoffLead:
    lead.status = status
    lead.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(lead)
    return lead


def _apply_lead_filters(
    query: Select,
    partner_id: str | None,
    start_at: datetime.datetime | None,
    end_before: datetime.datetime | None,
    statuses: list[str] | None,
) -> Select:
    if partner_id:
        query = query.filter(models.HandoffLead.partner_id == partner_id)
    if start_at:
        query = query.filter(models.HandoffLead.created_at >= start_at)
    if end_before:
        query = query.filter(models.HandoffLead.created_at < end_before)
    if statuses:
        query = query.filter(models.HandoffLead.status.in_(statuses))
    return query


async def get_lead_report(
    db: AsyncSession,
    partner_id: str | None = None,
    start_at: datetime.datetime | None = None,
    end_before: datetime.datetime | None = None,
    statuses: list[str] | None = None,
) -> tuple[int, int, list[tuple[str, str, int, int]]]:
    totals_query = select(
        func.count(models.HandoffLead.id),
        func.count(distinct(models.HandoffLead.user_id)),
    )
    totals_query = _apply_lead_filters(totals_query, partner_id, start_at, end_before, statuses)
    totals_result = await db.execute(totals_query)
    total_leads, unique_users = totals_result.one()

    by_partner_query = (
        select(
            models.HandoffLead.partner_id,
            models.Partner.name,
            func.count(models.HandoffLead.id),
            func.count(distinct(models.HandoffLead.user_id)),
        )
        .join(models.Partner, models.Partner.id == models.HandoffLead.partner_id)
        .group_by(models.HandoffLead.partner_id, models.Partner.name)
        .order_by(func.count(models.HandoffLead.id).desc(), models.Partner.name.asc())
    )
    by_partner_query = _apply_lead_filters(by_partner_query, partner_id, start_at, end_before, statuses)
    by_partner_result = await db.execute(by_partner_query)
    by_partner_rows = by_partner_result.all()

    return (
        int(total_leads or 0),
        int(unique_users or 0),
        [(str(pid), str(name), int(count or 0), int(users or 0)) for pid, name, count, users in by_partner_rows],
    )

