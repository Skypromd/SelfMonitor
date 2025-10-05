from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
from typing import List, Optional

async def create_audit_event(db: AsyncSession, event: schemas.AuditEventCreate) -> models.AuditEvent:
    db_event = models.AuditEvent(**event.dict())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event

async def query_audit_events(db: AsyncSession, user_id: Optional[str] = None) -> List[models.AuditEvent]:
    query = select(models.AuditEvent).order_by(models.AuditEvent.timestamp.desc())
    if user_id:
        query = query.filter(models.AuditEvent.user_id == user_id)

    result = await db.execute(query)
    return result.scalars().all()
