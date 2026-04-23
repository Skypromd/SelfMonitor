import datetime
import hashlib
import json
import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas

GENESIS_CHAIN_HASH = "0" * 64


def _canonical_timestamp(ts: datetime.datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    ts = ts.astimezone(datetime.timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _canonical_payload(
    *,
    event_id: uuid.UUID,
    user_id: str,
    action: str,
    details: Optional[dict],
    ts: datetime.datetime,
) -> str:
    payload = {
        "id": str(event_id),
        "user_id": user_id,
        "action": action,
        "details": details if details is not None else {},
        "timestamp": _canonical_timestamp(ts),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _compute_chain_hash(prev_hash: str, canonical: str) -> str:
    return hashlib.sha256(f"{prev_hash}|{canonical}".encode("utf-8")).hexdigest()


async def _last_event_for_user(db: AsyncSession, user_id: str) -> Optional[models.AuditEvent]:
    stmt = (
        select(models.AuditEvent)
        .where(models.AuditEvent.user_id == user_id)
        .order_by(desc(models.AuditEvent.timestamp), desc(models.AuditEvent.id))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_audit_event(db: AsyncSession, event: schemas.AuditEventCreate) -> models.AuditEvent:
    event_id = uuid.uuid4()
    ts = datetime.datetime.now(datetime.timezone.utc)
    last = await _last_event_for_user(db, event.user_id)
    if last is not None and last.chain_hash:
        prev_hash = last.chain_hash
    else:
        prev_hash = GENESIS_CHAIN_HASH
    canonical = _canonical_payload(
        event_id=event_id,
        user_id=event.user_id,
        action=event.action,
        details=event.details,
        ts=ts,
    )
    chain_hash = _compute_chain_hash(prev_hash, canonical)
    db_event = models.AuditEvent(
        id=event_id,
        timestamp=ts,
        user_id=event.user_id,
        action=event.action,
        details=event.details,
        prev_chain_hash=prev_hash,
        chain_hash=chain_hash,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def query_audit_events(db: AsyncSession, user_id: Optional[str] = None) -> List[models.AuditEvent]:
    query = select(models.AuditEvent).order_by(
        desc(models.AuditEvent.timestamp),
        desc(models.AuditEvent.id),
    )
    if user_id:
        query = query.filter(models.AuditEvent.user_id == user_id)

    result = await db.execute(query)
    return list(result.scalars().all())
