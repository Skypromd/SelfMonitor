"""Recompute CIS statement net vs matched bank credits."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models

_TOLERANCE_MIN_GBP = 1.0
_TOLERANCE_FRAC = 0.01


async def load_transactions_for_ids(
    db: AsyncSession,
    *,
    user_id: str,
    ids: list[uuid.UUID],
) -> dict[uuid.UUID, models.Transaction]:
    if not ids:
        return {}
    r = await db.execute(
        select(models.Transaction).where(
            models.Transaction.user_id == user_id,
            models.Transaction.id.in_(ids),
        )
    )
    rows = list(r.scalars().all())
    return {t.id: t for t in rows}


def _reconciliation_status_for_record(
    rec: models.CISRecord,
    bank_net_sum: float,
) -> str:
    if rec.evidence_status != "verified_with_statement":
        return "not_applicable"
    if not rec.matched_bank_transaction_ids:
        return "pending"
    tol = max(_TOLERANCE_MIN_GBP, _TOLERANCE_FRAC * abs(float(rec.net_paid_total or 0)))
    if abs(bank_net_sum - float(rec.net_paid_total)) <= tol:
        return "ok"
    return "needs_review"


async def recompute_cis_record_reconciliation(
    db: AsyncSession,
    *,
    rec: models.CISRecord,
) -> None:
    ids: list[uuid.UUID] = []
    raw = rec.matched_bank_transaction_ids
    if isinstance(raw, list):
        for x in raw:
            try:
                ids.append(uuid.UUID(str(x)))
            except (ValueError, TypeError):
                continue
    tx_map = await load_transactions_for_ids(db, user_id=rec.user_id, ids=ids)
    bank_net = sum(float(tx_map[i].amount) for i in ids if i in tx_map)
    rec.bank_net_observed_gbp = round(bank_net, 2)
    rec.reconciliation_status = _reconciliation_status_for_record(rec, bank_net)
    rec.updated_at = datetime.datetime.now(datetime.UTC)
