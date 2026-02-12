import datetime
from typing import List, Optional

from sqlalchemy import func
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
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=dedupe_window_hours)
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

