import datetime
import io
import json
import logging
import os
import sys
import uuid
import zipfile
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from . import cis_refund_tracker, crud, crud_cis, models, schemas
from .database import get_db
from .telemetry import setup_telemetry

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.internal_jwt import build_receipt_draft_create_user_id_dependency
from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_auth.plan_enforcement_log import log_plan_enforcement_denial
from libs.shared_auth.plan_limits import PlanLimits, get_plan_limits
from libs.shared_http.request_id import RequestIdMiddleware, get_request_id

app = FastAPI(
    title="Transactions Service",
    description="Stores and categorizes financial transactions.",
    version="1.0.0"
)

app.add_middleware(RequestIdMiddleware)

KAFKA_ENABLED: bool = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
logger = logging.getLogger(__name__)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()
if not os.environ.get("INTERNAL_SERVICE_SECRET", "").strip():
    raise RuntimeError("INTERNAL_SERVICE_SECRET must be set and non-empty")
get_user_id_for_receipt_draft_create = build_receipt_draft_create_user_id_dependency()

# --- Endpoints ---
@app.post(
    "/import",
    response_model=schemas.TransactionImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_transactions(
    request: schemas.TransactionImportRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
    db: AsyncSession = Depends(get_db),
):
    """Imports a batch of transactions for an account into the database."""
    existing_month = await crud.count_transactions_in_calendar_month(db, user_id=user_id)
    incoming = len(request.transactions)
    if existing_month + incoming > limits.transactions_per_month_limit:
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="transactions_per_month",
            reason="monthly_cap_exceeded",
            current=existing_month + incoming,
            limit_value=limits.transactions_per_month_limit,
            request_id=get_request_id(),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Monthly transaction limit ({limits.transactions_per_month_limit}) would be exceeded. "
                f"Recorded this month: {existing_month}, batch size: {incoming}. Upgrade your plan or wait until next month."
            ),
        )
    import_result = await crud.create_transactions(
        db,
        user_id=user_id,
        account_id=request.account_id,
        transactions=request.transactions,
    )
    if import_result.get("created_count", 0) > 0:
        try:
            n = await crud_cis.scan_user_for_cis_suspects(
                db, user_id=user_id, bearer_token=bearer_token
            )
            logger.info("cis_suspect_scan after import: %s new task(s)", n)
        except Exception as exc:
            logger.warning("cis_suspect_scan failed: %s", exc)
    return schemas.TransactionImportResponse(
        message="Import request accepted",
        imported_count=import_result["imported_count"],
        created_count=import_result["created_count"],
        reconciled_receipt_drafts=import_result["reconciled_receipt_drafts"],
        skipped_duplicates=import_result["skipped_duplicates"],
    )

@app.get("/accounts/{account_id}/transactions", response_model=List[schemas.Transaction])
async def get_transactions_for_account(
    account_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for a specific account belonging to the user from the database."""
    transactions = await crud.get_transactions_by_account(db, user_id=user_id, account_id=account_id)

    # Emit analytics event for transaction access
    if KAFKA_ENABLED and hasattr(app, 'emit_event') and transactions:
        try:
            await app.emit_event(
                topic="analytics.events",
                event_type="transaction_data_accessed",
                data={
                    "metric_name": "transaction_retrieval",
                    "metric_value": len(transactions),
                    "account_id": str(account_id),
                    "access_type": "account_specific",
                    "result_count": len(transactions)
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction access event: {str(e)}")

    return transactions

@app.get("/transactions/me", response_model=List[schemas.Transaction])
async def get_all_my_transactions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for the authenticated user across all accounts."""
    transactions = await crud.get_transactions_by_user(db, user_id=user_id)

    # Emit analytics event for comprehensive transaction access
    if KAFKA_ENABLED and hasattr(app, 'emit_event') and transactions:
        try:
            await app.emit_event(
                topic="analytics.events",
                event_type="transaction_data_accessed",
                data={
                    "metric_name": "comprehensive_transaction_view",
                    "metric_value": len(transactions),
                    "access_type": "all_accounts",
                    "result_count": len(transactions),
                    "unique_accounts": len(set(str(t.account_id) for t in transactions if hasattr(t, 'account_id')))
                },
                user_id=user_id
            )

            # Also track user engagement
            await app.emit_event(
                topic="user.events",
                event_type="user_transaction_overview_accessed",
                data={
                    "total_transactions": len(transactions),
                    "access_timestamp": int(uuid.uuid1().time),
                    "feature": "transaction_overview"
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction overview events: {str(e)}")

    return transactions

@app.patch("/transactions/{transaction_id}", response_model=schemas.Transaction)
async def update_transaction_category(
    transaction_id: uuid.UUID,
    update_request: schemas.TransactionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Updates the category of a single transaction in the database."""
    updated_transaction = await crud.update_transaction(
        db,
        user_id=user_id,
        transaction_id=transaction_id,
        update_request=update_request,
    )
    if not updated_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Emit transaction update event
    if KAFKA_ENABLED and hasattr(app, 'emit_event'):
        try:
            await app.emit_event(
                topic="transaction.events",
                event_type="transaction_category_updated",
                data={
                    "transaction_id": str(transaction_id),
                    "old_category": getattr(updated_transaction, 'previous_category', None),
                    "new_category": update_request.category,
                    "amount": float(updated_transaction.amount) if hasattr(updated_transaction, 'amount') else None,
                    "currency": getattr(updated_transaction, 'currency', 'USD'),
                    "description": getattr(updated_transaction, 'description', ''),
                    "update_source": "manual_categorization"
                },
                user_id=user_id,
                correlation_id=f"category_update_{transaction_id}"
            )

            # Also emit analytics event for categorization tracking
            await app.emit_event(
                topic="analytics.events",
                event_type="transaction_categorized",
                data={
                    "metric_name": "transaction_categorization",
                    "metric_value": 1.0,
                    "transaction_id": str(transaction_id),
                    "category": update_request.category,
                    "user_action": "manual"
                },
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to emit transaction update events: {str(e)}")

    return updated_transaction


@app.patch(
    "/transactions/receipt-drafts/{draft_transaction_id}",
    response_model=schemas.Transaction,
)
async def update_receipt_draft_transaction(
    draft_transaction_id: uuid.UUID,
    payload: schemas.ReceiptDraftUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Updates OCR-corrected fields on a receipt draft (amount, date, vendor, category)."""
    updated = await crud.update_receipt_draft(
        db, user_id=user_id, draft_transaction_id=draft_transaction_id, payload=payload
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="receipt_draft_not_found")
    return updated


@app.post("/transactions/receipt-drafts", response_model=schemas.ReceiptDraftCreateResponse)
async def create_receipt_draft_transaction(
    payload: schemas.ReceiptDraftCreateRequest,
    user_id: str = Depends(get_user_id_for_receipt_draft_create),
    db: AsyncSession = Depends(get_db),
):
    """Creates or reuses a receipt-derived draft transaction for tax expenses."""
    transaction, duplicated = await crud.create_or_get_receipt_draft_transaction(
        db,
        user_id=user_id,
        payload=payload,
    )
    return schemas.ReceiptDraftCreateResponse(transaction=transaction, duplicated=duplicated)


@app.get(
    "/transactions/receipt-drafts/unmatched",
    response_model=schemas.UnmatchedReceiptDraftsResponse,
)
async def list_unmatched_receipt_drafts(
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    candidate_limit: int = Query(default=5, ge=1, le=20),
    include_ignored: bool = Query(default=False),
    search_provider_transaction_id: str | None = Query(default=None),
    search_amount: float | None = Query(default=None, gt=0),
    search_date: datetime.date | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total, items = await crud.list_unmatched_receipt_drafts(
        db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        candidate_limit=candidate_limit,
        include_ignored=include_ignored,
        search_provider_transaction_id=search_provider_transaction_id,
        search_amount=search_amount,
        search_date=search_date,
    )
    return schemas.UnmatchedReceiptDraftsResponse(total=total, items=items)


@app.get(
    "/transactions/receipt-drafts/{draft_transaction_id}/candidates",
    response_model=schemas.ReceiptDraftCandidatesResponse,
)
async def get_receipt_draft_candidates(
    draft_transaction_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    include_ignored: bool = Query(default=True),
    search_provider_transaction_id: str | None = Query(default=None),
    search_amount: float | None = Query(default=None, gt=0),
    search_date: datetime.date | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction, candidates = await crud.get_receipt_draft_candidates(
            db,
            user_id=user_id,
            draft_transaction_id=draft_transaction_id,
            limit=limit,
            include_ignored=include_ignored,
            search_provider_transaction_id=search_provider_transaction_id,
            search_amount=search_amount,
            search_date=search_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return schemas.ReceiptDraftCandidatesResponse(
        draft_transaction=draft_transaction,
        total=len(candidates),
        items=candidates,
    )


@app.post(
    "/transactions/receipt-drafts/{draft_transaction_id}/ignore-candidate",
    response_model=schemas.ReceiptDraftStateUpdateResponse,
)
async def ignore_receipt_draft_candidate(
    draft_transaction_id: uuid.UUID,
    payload: schemas.ReceiptDraftIgnoreCandidateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction = await crud.ignore_receipt_draft_candidate(
            db,
            user_id=user_id,
            draft_transaction_id=draft_transaction_id,
            target_transaction_id=payload.target_transaction_id,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail in {"draft_not_found", "target_not_found"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    return schemas.ReceiptDraftStateUpdateResponse(draft_transaction=draft_transaction)


@app.post(
    "/transactions/receipt-drafts/{draft_transaction_id}/ignore",
    response_model=schemas.ReceiptDraftStateUpdateResponse,
)
async def ignore_receipt_draft(
    draft_transaction_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction = await crud.set_receipt_draft_status(
            db,
            user_id=user_id,
            draft_transaction_id=draft_transaction_id,
            status="ignored",
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "draft_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    return schemas.ReceiptDraftStateUpdateResponse(draft_transaction=draft_transaction)


@app.post(
    "/transactions/receipt-drafts/{draft_transaction_id}/reopen",
    response_model=schemas.ReceiptDraftStateUpdateResponse,
)
async def reopen_receipt_draft(
    draft_transaction_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction = await crud.set_receipt_draft_status(
            db,
            user_id=user_id,
            draft_transaction_id=draft_transaction_id,
            status="open",
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "draft_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    return schemas.ReceiptDraftStateUpdateResponse(draft_transaction=draft_transaction)


@app.post(
    "/transactions/receipt-drafts/{draft_transaction_id}/reconcile",
    response_model=schemas.ReceiptDraftManualReconcileResponse,
)
async def manual_reconcile_receipt_draft(
    draft_transaction_id: uuid.UUID,
    payload: schemas.ReceiptDraftManualReconcileRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        reconciled, removed_id = await crud.manual_reconcile_receipt_draft(
            db,
            user_id=user_id,
            draft_transaction_id=draft_transaction_id,
            target_transaction_id=payload.target_transaction_id,
        )
    except ValueError as exc:
        message = str(exc)
        if message in {"draft_not_found", "target_not_found"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        if message in {"draft_not_unmatched", "target_is_draft", "target_provider_conflict"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    return schemas.ReceiptDraftManualReconcileResponse(
        reconciled_transaction=reconciled,
        removed_transaction_id=removed_id,
    )


# --- CIS (variant B), evidence manifest, accountant delegation ---


@app.post(
    "/cis/records",
    response_model=schemas.CISRecordOut,
    status_code=status.HTTP_201_CREATED,
)
async def cis_create_record(
    body: schemas.CISRecordCreate,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
):
    att_json = None
    if body.attestation:
        att = body.attestation
        att_json = {
            "attested_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "attestation_version": att.attestation_version,
            "attestation_text": att.attestation_text,
            "attested_by_user_id": user_id,
            "client_context": att.client_context,
        }
    payload = body.model_dump(exclude={"attestation"})
    payload["attestation_json"] = att_json
    rec = await crud_cis.create_cis_record(
        db, user_id=user_id, bearer_token=bearer_token, payload=payload
    )
    return rec


@app.get("/cis/records", response_model=List[schemas.CISRecordOut])
async def cis_list_records(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud_cis.list_cis_records(db, user_id=user_id)


@app.get("/cis/records/{record_id}", response_model=schemas.CISRecordOut)
async def cis_get_record(
    record_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    rec = await crud_cis.get_cis_record(db, user_id=user_id, record_id=record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_record_not_found")
    return rec


@app.patch("/cis/records/{record_id}", response_model=schemas.CISRecordOut)
async def cis_patch_record(
    record_id: uuid.UUID,
    body: schemas.CISRecordPatch,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    rec = await crud_cis.patch_cis_record(
        db,
        user_id=user_id,
        bearer_token=bearer_token,
        record_id=record_id,
        updates=updates,
    )
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_record_not_found")
    return rec


@app.post("/cis/tasks/suspect", response_model=schemas.CISReviewTaskOut, status_code=status.HTTP_201_CREATED)
async def cis_create_suspect_task(
    body: schemas.CISSuspectTaskCreate,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await crud_cis.create_suspect_task(
            db,
            user_id=user_id,
            bearer_token=bearer_token,
            transaction_id=body.transaction_id,
            reason=body.reason,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "transaction_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=code) from exc
        if code == "open_task_already_exists":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code) from exc
        raise
    return task


@app.get("/cis/tasks", response_model=List[schemas.CISReviewTaskOut])
async def cis_list_tasks(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
):
    return await crud_cis.list_cis_tasks(db, user_id=user_id, status=status_filter)


@app.patch("/cis/tasks/{task_id}", response_model=schemas.CISReviewTaskOut)
async def cis_patch_task(
    task_id: uuid.UUID,
    body: schemas.CISReviewTaskPatch,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
):
    task = await crud_cis.update_cis_task(
        db,
        user_id=user_id,
        bearer_token=bearer_token,
        task_id=task_id,
        status=body.status,
        cis_record_id=body.cis_record_id,
        payer_label=body.payer_label,
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_task_not_found")
    return task


@app.post("/cis/tasks/scan", response_model=dict)
async def cis_scan_now(
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
    lookback_days: int = Query(default=120, ge=7, le=366),
):
    n = await crud_cis.scan_user_for_cis_suspects(
        db, user_id=user_id, bearer_token=bearer_token, lookback_days=lookback_days
    )
    return {"new_tasks": n}


@app.get("/cis/reminders/due", response_model=List[schemas.CISReviewTaskOut])
async def cis_reminders_due(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud_cis.tasks_due_reminder(db, user_id=user_id)


@app.get("/cis/reminders/notification-eligible", response_model=List[schemas.CISReviewTaskOut])
async def cis_reminders_notification_eligible(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Tasks due by date that also pass 72h hard + 2-in-7d soft throttle (for email/push worker)."""
    return await crud_cis.list_notification_eligible_tasks(db, user_id=user_id)


@app.post("/cis/reminders/{task_id}/mark-sent", response_model=schemas.CISReviewTaskOut)
async def cis_reminders_mark_sent(
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await crud_cis.mark_task_reminder_sent(db, user_id=user_id, task_id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_task_not_found")
    return task


@app.get("/cis/refund-tracker", response_model=dict)
async def cis_refund_tracker_endpoint(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await cis_refund_tracker.build_refund_tracker_snapshot(db, user_id=user_id)


@app.post("/cis/tasks/{task_id}/snooze-reminder", response_model=schemas.CISReviewTaskOut)
async def cis_snooze_reminder(
    task_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=365),
):
    if days not in (7, 14, 30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="snooze days must be 7, 14, or 30",
        )
    task = await crud_cis.bump_task_reminder(db, user_id=user_id, task_id=task_id, days=days)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_task_not_found")
    return task


@app.get("/cis/evidence-pack/manifest", response_model=schemas.EvidencePackManifestOut)
async def cis_evidence_manifest(
    user_id: str = Depends(get_current_user_id),
    limits: PlanLimits = Depends(get_plan_limits),
    db: AsyncSession = Depends(get_db),
):
    if limits.evidence_pack_tier == "none":
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="cis_evidence_pack",
            reason="evidence_tier_none",
            request_id=get_request_id(),
            extra={"tier": limits.evidence_pack_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CIS evidence pack is not included in your plan. Upgrade to Growth or higher.",
        )
    manifest = await crud_cis.build_evidence_manifest(db, user_id=user_id)
    return schemas.EvidencePackManifestOut(manifest=manifest)


@app.get("/cis/evidence-pack/zip")
async def cis_evidence_zip(
    user_id: str = Depends(get_current_user_id),
    limits: PlanLimits = Depends(get_plan_limits),
    db: AsyncSession = Depends(get_db),
):
    if limits.evidence_pack_tier == "none":
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="cis_evidence_pack_zip",
            reason="evidence_tier_none",
            request_id=get_request_id(),
            extra={"tier": limits.evidence_pack_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CIS evidence pack export is not included in your plan. Upgrade to Growth or higher.",
        )
    manifest = await crud_cis.build_evidence_manifest(db, user_id=user_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "cis-evidence-manifest.json",
            json.dumps(manifest, indent=2, default=str).encode("utf-8"),
        )
        notice = (
            (manifest.get("watermark_unverified_cis") or "")
            + "\n\n"
            + (manifest.get("export_legal_notice") or "")
        )
        zf.writestr("NOTICE.txt", notice.encode("utf-8"))
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="selfmonitor-cis-evidence-pack.zip"'
        },
    )


@app.post(
    "/accountant/delegations",
    response_model=schemas.AccountantDelegationOut,
    status_code=status.HTTP_201_CREATED,
)
async def accountant_create_delegation(
    body: schemas.AccountantDelegationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if body.can_submit_hmrc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="can_submit_hmrc must remain false until product policy allows accountant HMRC submit",
        )
    row = await crud_cis.create_delegation(
        db,
        client_user_id=user_id,
        accountant_user_id=body.accountant_user_id,
        scopes=body.scopes or ["read_reports", "read_transactions", "read_documents", "comment"],
        can_submit_hmrc=False,
        expires_at=body.expires_at,
    )
    return row


@app.get("/accountant/delegations", response_model=List[schemas.AccountantDelegationOut])
async def accountant_list_delegations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud_cis.list_delegations_for_client(db, client_user_id=user_id)


@app.delete("/accountant/delegations/{delegation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def accountant_revoke_delegation(
    delegation_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ok = await crud_cis.revoke_delegation(
        db, client_user_id=user_id, delegation_id=delegation_id
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="delegation_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
