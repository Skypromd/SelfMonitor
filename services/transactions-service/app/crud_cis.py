import datetime
import logging
import os
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.shared_cis.audit_actions import CISAuditAction
from libs.shared_compliance.audit_client import post_audit_event

from . import models
from .cis_reconciliation import recompute_cis_record_reconciliation
from .cis_reminder_throttle import append_sent_timestamp, reminder_send_allowed
from .cis_uk_calendar import (
    contractor_key_from_label,
    format_tax_month_label,
    uk_tax_month_for_date,
)

logger = logging.getLogger(__name__)

COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "").strip()


def transaction_matches_cis_heuristic(txn: models.Transaction) -> bool:
    if float(txn.amount) <= 0:
        return False
    d = (txn.description or "").lower()
    c = (txn.category or "").lower()
    if "cis" in d or "cis deduction" in d or "construction industry scheme" in d:
        return True
    if c in {"cis", "cis_income", "construction"}:
        return True
    return False


async def _audit(
    bearer_token: str,
    user_id: str,
    action: CISAuditAction,
    details: dict[str, Any] | None = None,
) -> None:
    if not COMPLIANCE_SERVICE_URL:
        return
    ok = await post_audit_event(
        compliance_base_url=COMPLIANCE_SERVICE_URL,
        bearer_token=bearer_token,
        user_id=user_id,
        action=str(action),
        details=details,
    )
    if not ok:
        logger.warning("CIS audit not recorded action=%s user=%s", action, user_id)


async def _open_task_exists_for_tx(
    db: AsyncSession, *, user_id: str, transaction_id: uuid.UUID
) -> bool:
    r = await db.execute(
        select(models.CISReviewTask).where(
            models.CISReviewTask.user_id == user_id,
            models.CISReviewTask.suspected_transaction_id == transaction_id,
            models.CISReviewTask.status == "open",
        )
    )
    return r.scalars().first() is not None


async def scan_user_for_cis_suspects(
    db: AsyncSession,
    *,
    user_id: str,
    bearer_token: str,
    lookback_days: int = 120,
) -> int:
    cutoff = datetime.date.today() - datetime.timedelta(days=lookback_days)
    r = await db.execute(
        select(models.Transaction).where(
            models.Transaction.user_id == user_id,
            models.Transaction.date >= cutoff,
            models.Transaction.amount > 0,
        )
    )
    rows = list(r.scalars().all())
    created = 0
    for txn in rows:
        if not transaction_matches_cis_heuristic(txn):
            continue
        if await _open_task_exists_for_tx(db, user_id=user_id, transaction_id=txn.id):
            continue
        task = models.CISReviewTask(
            id=uuid.uuid4(),
            user_id=user_id,
            status="open",
            suspected_transaction_id=txn.id,
            suspect_reason="heuristic_income_keyword",
            next_reminder_at=datetime.date.today(),
            reminder_meta={},
        )
        db.add(task)
        created += 1
        await _ensure_cis_obligation_for_suspect(db, user_id=user_id, txn=txn)
        await _audit(
            bearer_token,
            user_id,
            CISAuditAction.CIS_SUSPECTED_FROM_BANK_TRANSACTION,
            {"transaction_id": str(txn.id), "description": txn.description[:200]},
        )
    if created:
        await db.commit()
    return created


async def _ensure_cis_obligation_for_suspect(
    db: AsyncSession, *, user_id: str, txn: models.Transaction
) -> None:
    ty, tm = uk_tax_month_for_date(txn.date)
    label = format_tax_month_label(ty, tm)
    ckey = contractor_key_from_label((txn.description or "")[:200])
    r = await db.execute(
        select(models.CISObligation).where(
            models.CISObligation.user_id == user_id,
            models.CISObligation.cis_tax_month_label == label,
            models.CISObligation.contractor_key == ckey,
        )
    )
    if r.scalars().first() is not None:
        return
    db.add(
        models.CISObligation(
            id=uuid.uuid4(),
            user_id=user_id,
            cis_tax_month_label=label,
            contractor_key=ckey,
            status="MISSING",
        )
    )
    await db.flush()


async def create_suspect_task(
    db: AsyncSession,
    *,
    user_id: str,
    bearer_token: str,
    transaction_id: uuid.UUID,
    reason: str,
) -> models.CISReviewTask:
    r = await db.execute(
        select(models.Transaction).where(
            models.Transaction.user_id == user_id,
            models.Transaction.id == transaction_id,
        )
    )
    txn = r.scalars().first()
    if txn is None:
        raise ValueError("transaction_not_found")
    if await _open_task_exists_for_tx(db, user_id=user_id, transaction_id=transaction_id):
        raise ValueError("open_task_already_exists")
    task = models.CISReviewTask(
        id=uuid.uuid4(),
        user_id=user_id,
        status="open",
        suspected_transaction_id=transaction_id,
        suspect_reason=reason[:500],
        next_reminder_at=datetime.date.today(),
        reminder_meta={},
    )
    db.add(task)
    await _ensure_cis_obligation_for_suspect(db, user_id=user_id, txn=txn)
    await db.commit()
    await db.refresh(task)
    await _audit(
        bearer_token,
        user_id,
        CISAuditAction.CIS_SUSPECTED_FROM_BANK_TRANSACTION,
        {"transaction_id": str(transaction_id), "reason": reason},
    )
    return task


async def list_cis_tasks(
    db: AsyncSession,
    *,
    user_id: str,
    status: str | None = None,
) -> list[models.CISReviewTask]:
    q = select(models.CISReviewTask).where(models.CISReviewTask.user_id == user_id)
    if status:
        q = q.where(models.CISReviewTask.status == status)
    q = q.order_by(models.CISReviewTask.created_at.desc())
    r = await db.execute(q)
    return list(r.scalars().all())


async def update_cis_task(
    db: AsyncSession,
    *,
    user_id: str,
    bearer_token: str,
    task_id: uuid.UUID,
    status: str,
    cis_record_id: uuid.UUID | None,
    payer_label: str | None,
) -> models.CISReviewTask | None:
    r = await db.execute(
        select(models.CISReviewTask).where(
            models.CISReviewTask.user_id == user_id,
            models.CISReviewTask.id == task_id,
        )
    )
    task = r.scalars().first()
    if not task:
        return None
    task.status = status
    if cis_record_id is not None:
        task.cis_record_id = cis_record_id
    if payer_label is not None:
        task.payer_label = payer_label[:300]
    task.updated_at = datetime.datetime.now(datetime.UTC)
    await _apply_obligation_status_from_task(db, task=task, status=status)
    if status == "dismissed_not_cis":
        await _audit(
            bearer_token,
            user_id,
            CISAuditAction.CIS_CLASSIFIED_NOT_CIS,
            {"task_id": str(task_id), "transaction_id": str(task.suspected_transaction_id)},
        )
    elif status in ("resolved_verified", "resolved_unverified"):
        await _audit(
            bearer_token,
            user_id,
            CISAuditAction.CIS_CLASSIFIED_CONFIRMED,
            {
                "task_id": str(task_id),
                "resolution": status,
                "cis_record_id": str(cis_record_id) if cis_record_id else None,
            },
        )
    await db.commit()
    await db.refresh(task)
    return task


async def create_cis_record(
    db: AsyncSession,
    *,
    user_id: str,
    bearer_token: str,
    payload: dict[str, Any],
) -> models.CISRecord:
    rec = models.CISRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        contractor_name=str(payload["contractor_name"])[:300],
        period_start=payload["period_start"],
        period_end=payload["period_end"],
        gross_total=float(payload["gross_total"]),
        materials_total=float(payload.get("materials_total") or 0),
        cis_deducted_total=float(payload["cis_deducted_total"]),
        net_paid_total=float(payload["net_paid_total"]),
        evidence_status=str(payload["evidence_status"])[:64],
        document_id=(str(payload["document_id"])[:128] if payload.get("document_id") else None),
        source=str(payload["source"])[:64],
        matched_bank_transaction_ids=payload.get("matched_bank_transaction_ids"),
        attestation_json=payload.get("attestation_json"),
        report_status=str(payload.get("report_status") or "draft")[:64],
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    if rec.evidence_status == "self_attested_no_statement" and rec.attestation_json:
        await _audit(
            bearer_token,
            user_id,
            CISAuditAction.CIS_ATTESTATION_ACCEPTED_NO_STATEMENT,
            {"cis_record_id": str(rec.id), "version": rec.attestation_json.get("attestation_version")},
        )
    if rec.document_id:
        await _audit(
            bearer_token,
            user_id,
            CISAuditAction.CIS_STATEMENT_UPLOADED,
            {"cis_record_id": str(rec.id), "document_id": rec.document_id},
        )
    await _audit(
        bearer_token,
        user_id,
        CISAuditAction.CIS_AMOUNTS_SAVED,
        {
            "cis_record_id": str(rec.id),
            "evidence_status": rec.evidence_status,
            "cis_deducted_total": rec.cis_deducted_total,
        },
    )
    await recompute_cis_record_reconciliation(db, rec=rec)
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_cis_records(
    db: AsyncSession, *, user_id: str
) -> list[models.CISRecord]:
    r = await db.execute(
        select(models.CISRecord)
        .where(models.CISRecord.user_id == user_id)
        .order_by(models.CISRecord.period_end.desc())
    )
    return list(r.scalars().all())


async def get_cis_record(
    db: AsyncSession, *, user_id: str, record_id: uuid.UUID
) -> models.CISRecord | None:
    r = await db.execute(
        select(models.CISRecord).where(
            models.CISRecord.user_id == user_id,
            models.CISRecord.id == record_id,
        )
    )
    return r.scalars().first()


async def patch_cis_record(
    db: AsyncSession,
    *,
    user_id: str,
    bearer_token: str,
    record_id: uuid.UUID,
    updates: dict[str, Any],
) -> models.CISRecord | None:
    rec = await get_cis_record(db, user_id=user_id, record_id=record_id)
    if not rec:
        return None
    for k, v in updates.items():
        if hasattr(rec, k) and v is not None and k not in {"id", "user_id", "created_at"}:
            setattr(rec, k, v)
    rec.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(rec)
    await _audit(
        bearer_token,
        user_id,
        CISAuditAction.CIS_RECORD_UPDATED,
        {"cis_record_id": str(record_id), "fields": list(updates.keys())},
    )
    if any(
        k in updates
        for k in ("matched_bank_transaction_ids", "net_paid_total", "evidence_status", "document_id")
    ):
        await recompute_cis_record_reconciliation(db, rec=rec)
        await db.commit()
        await db.refresh(rec)
    return rec


async def tasks_due_reminder(
    db: AsyncSession, *, user_id: str, on_or_before: datetime.date | None = None
) -> list[models.CISReviewTask]:
    d = on_or_before or datetime.date.today()
    r = await db.execute(
        select(models.CISReviewTask).where(
            models.CISReviewTask.user_id == user_id,
            models.CISReviewTask.status == "open",
            models.CISReviewTask.next_reminder_at.is_not(None),
            models.CISReviewTask.next_reminder_at <= d,
        )
    )
    return list(r.scalars().all())


async def list_notification_eligible_tasks(
    db: AsyncSession, *, user_id: str
) -> list[models.CISReviewTask]:
    due = await tasks_due_reminder(db, user_id=user_id)
    now = datetime.datetime.now(datetime.UTC)
    out: list[models.CISReviewTask] = []
    for t in due:
        allowed, _reason = reminder_send_allowed(t.reminder_meta, now)
        if allowed:
            out.append(t)
    return out


async def mark_task_reminder_sent(
    db: AsyncSession, *, user_id: str, task_id: uuid.UUID
) -> models.CISReviewTask | None:
    r = await db.execute(
        select(models.CISReviewTask).where(
            models.CISReviewTask.user_id == user_id,
            models.CISReviewTask.id == task_id,
        )
    )
    task = r.scalars().first()
    if not task:
        return None
    now = datetime.datetime.now(datetime.UTC)
    task.reminder_meta = append_sent_timestamp(
        task.reminder_meta if isinstance(task.reminder_meta, dict) else {},
        now,
    )
    task.updated_at = now
    await db.commit()
    await db.refresh(task)
    logger.info("cis_reminder_marked_sent task_id=%s user_id=%s", task_id, user_id)
    return task


async def bump_task_reminder(
    db: AsyncSession, *, user_id: str, task_id: uuid.UUID, days: int = 30
) -> models.CISReviewTask | None:
    r = await db.execute(
        select(models.CISReviewTask).where(
            models.CISReviewTask.user_id == user_id,
            models.CISReviewTask.id == task_id,
        )
    )
    task = r.scalars().first()
    if not task:
        return None
    base = task.next_reminder_at or datetime.date.today()
    task.next_reminder_at = base + datetime.timedelta(days=days)
    task.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(task)
    return task


async def _apply_obligation_status_from_task(
    db: AsyncSession, *, task: models.CISReviewTask, status: str
) -> None:
    if not task.suspected_transaction_id:
        return
    r = await db.execute(
        select(models.Transaction).where(
            models.Transaction.user_id == task.user_id,
            models.Transaction.id == task.suspected_transaction_id,
        )
    )
    txn = r.scalars().first()
    if not txn:
        return
    ty, tm = uk_tax_month_for_date(txn.date)
    label = format_tax_month_label(ty, tm)
    label_text = (task.payer_label or txn.description or "")[:200]
    ckey = contractor_key_from_label(label_text)
    obr = await db.execute(
        select(models.CISObligation).where(
            models.CISObligation.user_id == task.user_id,
            models.CISObligation.cis_tax_month_label == label,
            models.CISObligation.contractor_key == ckey,
        )
    )
    row = obr.scalars().first()
    if not row:
        return
    if status == "dismissed_not_cis":
        row.status = "NOT_CIS"
    elif status == "resolved_verified":
        row.status = "VERIFIED"
    elif status == "resolved_unverified":
        row.status = "UNVERIFIED"
    row.updated_at = datetime.datetime.now(datetime.UTC)


async def list_cis_obligations(db: AsyncSession, *, user_id: str) -> list[models.CISObligation]:
    r = await db.execute(
        select(models.CISObligation)
        .where(models.CISObligation.user_id == user_id)
        .order_by(models.CISObligation.cis_tax_month_label.desc())
    )
    return list(r.scalars().all())


async def build_evidence_manifest(
    db: AsyncSession,
    *,
    user_id: str,
    tier: str = "full",
) -> dict[str, Any]:
    tier_l = (tier or "basic").strip().lower()
    if tier_l not in ("basic", "full"):
        tier_l = "basic"
    records = await list_cis_records(db, user_id=user_id)
    tasks = await list_cis_tasks(db, user_id=user_id, status=None)
    unverified = [r for r in records if r.evidence_status == "self_attested_no_statement"]
    watermark = (
        "UNVERIFIED CIS (no statement) — amounts below marked self_attested_no_statement. "
        "Not a substitute for official HMRC submissions."
    )
    base: dict[str, Any] = {
        "schema_version": "mynettax-evidence-pack-v1",
        "pack_tier": tier_l,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "user_id": user_id,
        "watermark_unverified_cis": watermark,
        "summary": {
            "verified_records": len([r for r in records if r.evidence_status == "verified_with_statement"]),
            "unverified_records": len(unverified),
            "open_tasks": len([t for t in tasks if t.status == "open"]),
        },
        "export_legal_notice": (
            "This manifest is for your accountant and internal evidence. "
            "HMRC may request CIS statements for verified figures."
        ),
    }
    if tier_l == "basic":
        base["cis_records"] = [
            {
                "id": str(r.id),
                "contractor_name": r.contractor_name,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "evidence_status": r.evidence_status,
                "cis_deducted_total": r.cis_deducted_total,
                "has_document": bool(r.document_id),
            }
            for r in records
        ]
        base["cis_tasks"] = {"open": base["summary"]["open_tasks"], "total": len(tasks)}
        return base

    base["cis_records"] = [
        {
            "id": str(r.id),
            "contractor_name": r.contractor_name,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "evidence_status": r.evidence_status,
            "cis_deducted_total": r.cis_deducted_total,
            "report_status": r.report_status,
            "document_id": r.document_id,
            "matched_bank_transaction_ids": r.matched_bank_transaction_ids or [],
            "reconciliation_status": r.reconciliation_status,
            "bank_net_observed_gbp": r.bank_net_observed_gbp,
            "attestation_present": bool(r.attestation_json),
        }
        for r in records
    ]
    base["cis_tasks"] = [
        {
            "id": str(t.id),
            "status": t.status,
            "suspected_transaction_id": str(t.suspected_transaction_id)
            if t.suspected_transaction_id
            else None,
            "suspect_reason": t.suspect_reason,
        }
        for t in tasks
    ]
    base["audit_summary"] = {
        "note": "Full tier includes reconciliation fields and task-level detail for accountant review.",
    }
    return base


# --- Accountant delegations ---


async def create_delegation(
    db: AsyncSession,
    *,
    client_user_id: str,
    accountant_user_id: str,
    scopes: list[str],
    can_submit_hmrc: bool = False,
    expires_at: datetime.datetime | None = None,
) -> models.AccountantDelegation:
    d = models.AccountantDelegation(
        id=uuid.uuid4(),
        client_user_id=client_user_id,
        accountant_user_id=accountant_user_id,
        scopes=scopes,
        can_submit_hmrc=can_submit_hmrc,
        expires_at=expires_at,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def list_delegations_for_client(
    db: AsyncSession, *, client_user_id: str
) -> list[models.AccountantDelegation]:
    r = await db.execute(
        select(models.AccountantDelegation).where(
            models.AccountantDelegation.client_user_id == client_user_id,
            models.AccountantDelegation.revoked_at.is_(None),
        )
    )
    return list(r.scalars().all())


async def revoke_delegation(
    db: AsyncSession, *, client_user_id: str, delegation_id: uuid.UUID
) -> bool:
    r = await db.execute(
        select(models.AccountantDelegation).where(
            models.AccountantDelegation.client_user_id == client_user_id,
            models.AccountantDelegation.id == delegation_id,
        )
    )
    row = r.scalars().first()
    if not row:
        return False
    row.revoked_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    return True
