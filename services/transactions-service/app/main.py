import datetime
import json
import logging
import os
import re
import sys
import uuid
from pathlib import Path
from typing import List

import httpx
from jose import jwt as jose_jwt

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from libs.shared_auth.internal_jwt import build_receipt_draft_create_user_id_dependency
from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_auth.plan_enforcement_log import log_plan_enforcement_denial
from libs.shared_auth.plan_limits import PlanLimits, get_plan_limits
from libs.shared_cis.audit_actions import CISAuditAction
from libs.shared_compliance.audit_client import post_audit_event
from libs.shared_http.request_id import RequestIdMiddleware, get_request_id

from . import (
    cis_evidence_share,
    cis_refund_tracker,
    crud,
    crud_business,
    crud_cis,
    models,
    schemas,
)
from .database import get_db
from .telemetry import setup_telemetry

app = FastAPI(
    title="Transactions Service",
    description="Stores and categorizes financial transactions.",
    version="1.0.0"
)

app.add_middleware(RequestIdMiddleware)

KAFKA_ENABLED: bool = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
logger = logging.getLogger(__name__)

FINOPS_MONITOR_URL = os.getenv("FINOPS_MONITOR_URL", "http://finops-monitor:8021").rstrip("/")


async def _notify_finops_dashboard_transaction(user_id: str) -> None:
    secret = os.environ.get("INTERNAL_SERVICE_SECRET", "").strip()
    if not secret:
        return
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(
                f"{FINOPS_MONITOR_URL}/internal/dashboard-transaction-event",
                json={"user_id": user_id},
                headers={"X-Internal-Token": secret},
            )
    except Exception as exc:
        logger.warning("finops dashboard notify failed: %s", exc)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()
if not os.environ.get("INTERNAL_SERVICE_SECRET", "").strip():
    raise RuntimeError("INTERNAL_SERVICE_SECRET must be set and non-empty")
get_user_id_for_receipt_draft_create = build_receipt_draft_create_user_id_dependency()


async def get_active_business_id(
    user_id: str = Depends(get_current_user_id),
    x_business_id: str | None = Header(default=None, alias="X-Business-Id"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    default_id = crud_business.default_business_uuid(user_id)
    await crud_business.ensure_default_business(db, user_id, default_id)
    if not x_business_id or not str(x_business_id).strip():
        return default_id
    try:
        bid = uuid.UUID(str(x_business_id).strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid X-Business-Id") from exc
    if bid == default_id:
        return bid
    if not await crud_business.user_owns_business(db, user_id, bid):
        raise HTTPException(status_code=404, detail="business not found")
    return bid


def _mint_short_lived_compliance_bearer(user_id: str) -> str | None:
    secret = os.environ.get("AUTH_SECRET_KEY", "").strip()
    if not secret:
        return None
    exp = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + 120
    return jose_jwt.encode({"sub": user_id, "exp": exp}, secret, algorithm="HS256")


@app.get("/businesses", response_model=List[schemas.UserBusinessOut])
async def list_user_businesses(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    default_id = crud_business.default_business_uuid(user_id)
    await crud_business.ensure_default_business(db, user_id, default_id)
    return await crud_business.list_businesses(db, user_id)


@app.post("/businesses", response_model=schemas.UserBusinessOut, status_code=status.HTTP_201_CREATED)
async def create_user_business(
    body: schemas.UserBusinessCreate,
    user_id: str = Depends(get_current_user_id),
    limits: PlanLimits = Depends(get_plan_limits),
    db: AsyncSession = Depends(get_db),
):
    if limits.plan != "business":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="multi_business_requires_business_plan",
        )
    default_id = crud_business.default_business_uuid(user_id)
    await crud_business.ensure_default_business(db, user_id, default_id)
    n = await crud_business.count_businesses(db, user_id)
    if n >= crud_business.MAX_BUSINESSES_BUSINESS_PLAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="business_limit_reached",
        )
    return await crud_business.create_business(db, user_id=user_id, display_name=body.display_name)


@app.patch("/businesses/{business_id}", response_model=schemas.UserBusinessOut)
async def rename_user_business(
    business_id: uuid.UUID,
    body: schemas.UserBusinessRename,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    row = await crud_business.rename_business(
        db, user_id=user_id, business_id=business_id, display_name=body.display_name
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="business not found")
    return row


# --- Endpoints ---
@app.post(
    "/import",
    response_model=schemas.TransactionImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_transactions(
    request: schemas.TransactionImportRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    business_id: uuid.UUID = Depends(get_active_business_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
    db: AsyncSession = Depends(get_db),
):
    """Imports a batch of transactions for an account into the database."""
    existing_month = await crud.count_transactions_in_calendar_month(
        db, user_id=user_id, business_id=business_id
    )
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
            compliance_bearer_token=bearer_token,
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
        background_tasks.add_task(_notify_finops_dashboard_transaction, user_id)
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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for a specific account belonging to the user from the database."""
    transactions = await crud.get_transactions_by_account(
        db, user_id=user_id, account_id=account_id, business_id=business_id
    )

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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for the authenticated user across all accounts."""
    transactions = await crud.get_transactions_by_user(db, user_id=user_id, business_id=business_id)

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


@app.get("/transactions/readiness")
async def get_transaction_readiness(
    user_id: str = Depends(get_current_user_id),
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns a tax-readiness score, blocker counts, and per-blocker metadata for the authenticated user."""
    transactions = await crud.get_transactions_by_user(db, user_id=user_id, business_id=business_id)

    total = len(transactions)
    if total == 0:
        return {
            "uncategorized_count": 0,
            "missing_business_pct": 0,
            "unmatched_receipts": 0,
            "cis_unverified": 0,
            "score": 100,
            "blockers": [],
            "today_list": [],
        }

    uncategorized_count = sum(
        1 for t in transactions if not getattr(t, "tax_category", None) and not getattr(t, "category", None)
    )
    missing_business_pct = sum(
        1 for t in transactions
        if getattr(t, "amount", 0) < 0 and getattr(t, "business_use_percent", None) is None
    )

    # unmatched receipt drafts — query directly from crud
    try:
        unmatched_count, _ = await crud.list_unmatched_receipt_drafts(
            db, user_id=user_id, limit=1, offset=0
        )
    except Exception:
        unmatched_count = 0

    # CIS: count unverified records for this user
    try:
        cis_records = await crud_cis.get_cis_records(db, user_id=user_id)
        cis_unverified = sum(
            1 for r in cis_records if getattr(r, "verification_status", "unverified") == "unverified"
        )
    except Exception:
        cis_unverified = 0

    blockers_raw = blockers = uncategorized_count + missing_business_pct + unmatched_count + cis_unverified
    score = max(0, round(100 - (blockers_raw / max(total, 1)) * 100))

    def _impact(count: int) -> int:
        return min(30, round(count / max(total, 1) * 100))

    blocker_list = []
    if uncategorized_count:
        blocker_list.append({
            "id": "uncategorized_transactions",
            "label": "Uncategorised transactions",
            "count": uncategorized_count,
            "severity": "blocking" if uncategorized_count > 10 else "attention",
            "estimated_minutes": max(2, min(uncategorized_count * 1, 30)),
            "impact_points": _impact(uncategorized_count),
            "action_label": "Categorise now",
            "action_route": "/transactions?filter=uncategorised",
        })
    if missing_business_pct:
        blocker_list.append({
            "id": "missing_business_pct",
            "label": "Expenses missing business-use %",
            "count": missing_business_pct,
            "severity": "attention",
            "estimated_minutes": max(2, min(missing_business_pct * 1, 20)),
            "impact_points": _impact(missing_business_pct),
            "action_label": "Set business use",
            "action_route": "/transactions?filter=uncategorised",
        })
    if unmatched_count:
        blocker_list.append({
            "id": "unmatched_receipts",
            "label": "Unmatched receipts",
            "count": unmatched_count,
            "severity": "attention",
            "estimated_minutes": max(2, min(unmatched_count * 2, 20)),
            "impact_points": _impact(unmatched_count),
            "action_label": "Match receipts",
            "action_route": "/transactions?filter=no_receipt",
        })
    if cis_unverified:
        blocker_list.append({
            "id": "cis_unverified",
            "label": "CIS records unverified",
            "count": cis_unverified,
            "severity": "blocking",
            "estimated_minutes": max(3, min(cis_unverified * 3, 30)),
            "impact_points": _impact(cis_unverified),
            "action_label": "Verify CIS",
            "action_route": "/cis-refund-tracker",
        })

    # Sort by severity then impact: blocking first, then attention, then info
    severity_order = {"blocking": 0, "attention": 1, "info": 2}
    blocker_list.sort(key=lambda b: (severity_order.get(b["severity"], 9), -b["impact_points"]))

    today_list = blocker_list[:3]

    return {
        "uncategorized_count": uncategorized_count,
        "missing_business_pct": missing_business_pct,
        "unmatched_receipts": unmatched_count,
        "cis_unverified": cis_unverified,
        "score": score,
        "blockers": blocker_list,
        "today_list": today_list,
    }


@app.get("/transactions/tax-reserve")
async def get_tax_reserve(
    user_id: str = Depends(get_current_user_id),
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns an estimated tax reserve for the current tax year based on transactions."""
    transactions = await crud.get_transactions_by_user(db, user_id=user_id, business_id=business_id)

    income = sum(float(getattr(t, "amount", 0)) for t in transactions if float(getattr(t, "amount", 0)) > 0)
    expenses = sum(abs(float(getattr(t, "amount", 0))) for t in transactions if float(getattr(t, "amount", 0)) < 0)

    # CIS deductions already withheld
    try:
        cis_records = await crud_cis.get_cis_records(db, user_id=user_id)
        cis_deductions = sum(
            float(getattr(r, "cis_withheld_gbp", 0) or 0)
            for r in cis_records
            if getattr(r, "verification_status", "unverified") == "verified"
        )
        cis_unverified_deductions = sum(
            float(getattr(r, "cis_withheld_gbp", 0) or 0)
            for r in cis_records
            if getattr(r, "verification_status", "unverified") == "unverified"
        )
    except Exception:
        cis_deductions = 0.0
        cis_unverified_deductions = 0.0

    profit = max(0.0, income - expenses)

    # Simplified UK tax estimate (2025/26): personal allowance £12,570
    personal_allowance = 12570.0
    basic_rate_limit = 50270.0
    taxable_profit = max(0.0, profit - personal_allowance)
    basic_rate_tax = min(taxable_profit, max(0.0, basic_rate_limit - personal_allowance)) * 0.20
    higher_rate_tax = max(0.0, taxable_profit - (basic_rate_limit - personal_allowance)) * 0.40
    income_tax = round(basic_rate_tax + higher_rate_tax, 2)

    # Class 4 NIC: 6% on profit £12,570–£50,270, 2% above
    class4_lower = max(0.0, min(profit, basic_rate_limit) - personal_allowance) * 0.06
    class4_upper = max(0.0, profit - basic_rate_limit) * 0.02
    class4_nic = round(class4_lower + class4_upper, 2)

    total_tax = round(income_tax + class4_nic, 2)
    net_due = round(max(0.0, total_tax - cis_deductions), 2)

    confidence = "high" if len(transactions) >= 20 else "medium" if len(transactions) >= 5 else "low"

    return {
        "income_gbp": round(income, 2),
        "expenses_gbp": round(expenses, 2),
        "profit_gbp": round(profit, 2),
        "income_tax_gbp": income_tax,
        "class4_nic_gbp": class4_nic,
        "total_tax_estimated_gbp": total_tax,
        "cis_deductions_verified_gbp": round(cis_deductions, 2),
        "cis_deductions_unverified_gbp": round(cis_unverified_deductions, 2),
        "net_tax_due_gbp": net_due,
        "confidence": confidence,
        "disclaimer": "This is an estimate only. Consult a qualified accountant before filing.",
    }


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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    """Updates OCR-corrected fields on a receipt draft (amount, date, vendor, category)."""
    updated = await crud.update_receipt_draft(
        db,
        user_id=user_id,
        business_id=business_id,
        draft_transaction_id=draft_transaction_id,
        payload=payload,
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
    default_id = crud_business.default_business_uuid(user_id)
    await crud_business.ensure_default_business(db, user_id, default_id)
    transaction, duplicated = await crud.create_or_get_receipt_draft_transaction(
        db,
        user_id=user_id,
        business_id=default_id,
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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction, candidates = await crud.get_receipt_draft_candidates(
            db,
            user_id=user_id,
            business_id=business_id,
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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction = await crud.ignore_receipt_draft_candidate(
            db,
            user_id=user_id,
            business_id=business_id,
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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction = await crud.set_receipt_draft_status(
            db,
            user_id=user_id,
            business_id=business_id,
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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_transaction = await crud.set_receipt_draft_status(
            db,
            user_id=user_id,
            business_id=business_id,
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
    business_id: uuid.UUID = Depends(get_active_business_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        reconciled, removed_id = await crud.manual_reconcile_receipt_draft(
            db,
            user_id=user_id,
            business_id=business_id,
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


@app.post("/cis/records/{record_id}/auto-match", response_model=schemas.CISAutoMatchResult)
async def cis_auto_match_record(
    record_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-match bank transactions to a CIS record by net_paid_total amount ± tolerance.
    Returns candidates and, if exactly one candidate is within tolerance, applies the match.
    """
    from sqlalchemy import select as _select

    from .cis_reconciliation import (
        _TOLERANCE_FRAC,
        _TOLERANCE_MIN_GBP,
        recompute_cis_record_reconciliation,
    )

    rec = await crud_cis.get_cis_record(db, user_id=user_id, record_id=record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_record_not_found")

    net = float(rec.net_paid_total or 0)
    tol = max(_TOLERANCE_MIN_GBP, _TOLERANCE_FRAC * abs(net))

    # Scan bank transactions in the 90-day window around the CIS period
    import datetime as _dt
    period_start = rec.period_start if isinstance(rec.period_start, _dt.date) else rec.period_start
    window_start = period_start - _dt.timedelta(days=14)
    window_end = rec.period_end + _dt.timedelta(days=30) if isinstance(rec.period_end, _dt.date) else _dt.date.today()

    r = await db.execute(
        _select(models.Transaction).where(
            models.Transaction.user_id == user_id,
            models.Transaction.amount > 0,
            models.Transaction.date >= window_start,
            models.Transaction.date <= window_end,
        )
    )
    txns = list(r.scalars().all())

    candidates = []
    within_tol = []
    for tx in txns:
        delta = abs(float(tx.amount) - net)
        in_tol = delta <= tol
        candidates.append(schemas.CISAutoMatchCandidate(
            transaction_id=str(tx.id),
            date=tx.date,
            description=tx.description,
            amount=float(tx.amount),
            delta_gbp=round(delta, 2),
            within_tolerance=in_tol,
        ))
        if in_tol:
            within_tol.append(tx)

    # Sort closest first
    candidates.sort(key=lambda c: c.delta_gbp)

    auto_applied = False
    if len(within_tol) == 1:
        rec.matched_bank_transaction_ids = [str(within_tol[0].id)]
        await recompute_cis_record_reconciliation(db, rec=rec)
        await db.commit()
        await db.refresh(rec)
        auto_applied = True

    return schemas.CISAutoMatchResult(
        record_id=str(record_id),
        net_paid_total=net,
        tolerance_gbp=round(tol, 2),
        candidates=candidates[:10],
        auto_applied=auto_applied,
        reconciliation_status=rec.reconciliation_status,
        bank_net_observed_gbp=rec.bank_net_observed_gbp,
    )


@app.post("/cis/records/{record_id}/set-matched-transactions", response_model=schemas.CISRecordOut)
async def cis_set_matched_transactions(
    record_id: uuid.UUID,
    body: schemas.CISManualMatchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually set the matched bank transaction IDs for a CIS record and recompute reconciliation.
    Accepts a list of transaction UUIDs. Validates all belong to the user.
    """
    from sqlalchemy import select as _select

    from .cis_reconciliation import recompute_cis_record_reconciliation

    rec = await crud_cis.get_cis_record(db, user_id=user_id, record_id=record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_record_not_found")

    # Validate all transaction IDs exist and belong to this user
    r = await db.execute(
        _select(models.Transaction).where(
            models.Transaction.user_id == user_id,
            models.Transaction.id.in_(body.transaction_ids),
        )
    )
    found = {tx.id for tx in r.scalars().all()}
    missing_ids = [str(tid) for tid in body.transaction_ids if tid not in found]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"transaction_not_found: {', '.join(missing_ids[:5])}",
        )

    rec.matched_bank_transaction_ids = [str(tid) for tid in body.transaction_ids]
    await recompute_cis_record_reconciliation(db, rec=rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@app.get("/cis/records/{record_id}/upload-guide")
async def cis_record_upload_guide(
    record_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a structured "what to upload to become verified" guide for a CIS record.
    Lists concrete next steps with expected document types.
    """
    rec = await crud_cis.get_cis_record(db, user_id=user_id, record_id=record_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cis_record_not_found")

    verified = rec.evidence_status == "verified_with_statement"
    steps = []
    if not verified:
        steps.append({
            "step": 1,
            "action": "obtain_statement",
            "title": "Obtain CIS300 / Deduction Statement",
            "description": (
                f"Contact '{rec.contractor_name}' and request their CIS300 monthly return or "
                "a subcontractor deduction statement for the period "
                f"{rec.period_start} to {rec.period_end}."
            ),
            "accepted_formats": ["PDF", "JPG/PNG (clear photo)", "XLSX"],
            "hmrc_reference": "CIS300 form or equivalent contractor-issued statement",
        })
        steps.append({
            "step": 2,
            "action": "upload",
            "title": "Upload Statement to CIS Control Centre",
            "description": "Go to the CIS Refund Tracker, find this contractor, click 'Upload statement' and attach the document.",
            "accepted_formats": ["PDF", "JPG", "PNG", "XLSX"],
            "hmrc_reference": None,
        })
        steps.append({
            "step": 3,
            "action": "verify_amounts",
            "title": "Confirm Key Amounts Match",
            "description": (
                f"The statement must show CIS deducted: £{rec.cis_deducted_total:.2f}, "
                f"net paid: £{rec.net_paid_total:.2f}. Any discrepancy triggers review."
            ),
            "accepted_formats": None,
            "hmrc_reference": None,
        })

    recon_status = rec.reconciliation_status
    if recon_status == "needs_review":
        steps.append({
            "step": len(steps) + 1,
            "action": "reconcile_bank",
            "title": "Reconcile Bank Transaction",
            "description": (
                "The bank net received differs from the declared net by more than the tolerance. "
                "Use the Auto-match tool in the CIS Control Centre to link the correct bank transaction, "
                "or manually select the matching payment."
            ),
            "accepted_formats": None,
            "hmrc_reference": None,
        })
    elif recon_status == "pending":
        steps.append({
            "step": len(steps) + 1,
            "action": "link_bank_transaction",
            "title": "Link a Bank Transaction",
            "description": (
                "No bank transaction has been linked to this CIS record yet. "
                "Use 'Auto-match' in the CIS Control Centre to automatically find the payment."
            ),
            "accepted_formats": None,
            "hmrc_reference": None,
        })

    return {
        "record_id": str(record_id),
        "contractor_name": rec.contractor_name,
        "period_start": str(rec.period_start),
        "period_end": str(rec.period_end),
        "cis_deducted_total": rec.cis_deducted_total,
        "net_paid_total": rec.net_paid_total,
        "evidence_status": rec.evidence_status,
        "reconciliation_status": recon_status,
        "is_verified": verified,
        "steps": steps,
    }


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


@app.get("/cis/obligations", response_model=List[schemas.CISObligationOut])
async def cis_list_obligations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud_cis.list_cis_obligations(db, user_id=user_id)


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


_CIS_STATEMENT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB hard cap
_CIS_ALLOWED_MIME_PREFIXES = ("application/pdf", "image/")


def _parse_cis_statement_text(text: str) -> dict:
    """Extract CIS statement fields from plain text via regex patterns."""

    def _find_amount(patterns: list[str], src: str) -> float | None:
        for pat in patterns:
            m = re.search(pat, src, re.IGNORECASE)
            if m:
                raw = m.group(1).replace(",", "").replace("£", "").strip()
                try:
                    return float(raw)
                except ValueError:
                    pass
        return None

    def _find_date(patterns: list[str], src: str) -> str | None:
        for pat in patterns:
            m = re.search(pat, src, re.IGNORECASE)
            if m:
                try:
                    day = int(m.group(1))
                    month_raw = m.group(2)
                    year = int(m.group(3))
                    months = {
                        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                        "may": 5, "jun": 6, "jul": 7, "aug": 8,
                        "sep": 9, "oct": 10, "nov": 11, "dec": 12,
                    }
                    if month_raw.isdigit():
                        month = int(month_raw)
                    else:
                        month = months.get(month_raw[:3].lower(), 0)
                    if 1 <= month <= 12 and 1 <= day <= 31 and year >= 2000:
                        return f"{year:04d}-{month:02d}-{day:02d}"
                except (ValueError, IndexError):
                    pass
        return None

    contractor = None
    for pat in [
        r"contractor[:\s]+([A-Za-z0-9 &.,'-]{2,80})",
        r"company[:\s]+([A-Za-z0-9 &.,'-]{2,80})",
        r"subcontractor paid by[:\s]+([A-Za-z0-9 &.,'-]{2,80})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            contractor = m.group(1).strip()
            break

    date_patterns = [
        r"(\d{1,2})[/\-. ](\d{1,2}|[A-Za-z]+)[/\-. ](\d{4})",
    ]
    period_start = _find_date(date_patterns, text)
    # Find second date occurrence for period end
    all_dates = re.findall(r"(\d{1,2})[/\-. ](\d{1,2}|[A-Za-z]+)[/\-. ](\d{4})", text, re.IGNORECASE)
    period_end = None
    parsed_dates: list[str] = []
    for d in all_dates:
        day, month_raw, year = int(d[0]), d[1], int(d[2])
        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                  "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        month = int(month_raw) if month_raw.isdigit() else months.get(month_raw[:3].lower(), 0)
        if 1 <= month <= 12 and 1 <= day <= 31 and year >= 2000:
            parsed_dates.append(f"{year:04d}-{month:02d}-{day:02d}")
    if parsed_dates:
        period_start = parsed_dates[0]
        period_end = parsed_dates[-1] if len(parsed_dates) > 1 else parsed_dates[0]

    gross = _find_amount([
        r"gross[:\s£]+([\d,]+\.?\d*)",
        r"gross payment[:\s£]+([\d,]+\.?\d*)",
        r"total gross[:\s£]+([\d,]+\.?\d*)",
    ], text)
    materials = _find_amount([
        r"materials?[:\s£]+([\d,]+\.?\d*)",
        r"cost of materials?[:\s£]+([\d,]+\.?\d*)",
    ], text)
    cis_deducted = _find_amount([
        r"(?:cis |tax |deduction)[:\s£]*deducted[:\s£]+([\d,]+\.?\d*)",
        r"tax deducted[:\s£]+([\d,]+\.?\d*)",
        r"cis deducted[:\s£]+([\d,]+\.?\d*)",
        r"deduction[:\s£]+([\d,]+\.?\d*)",
    ], text)
    net_paid = _find_amount([
        r"net[:\s£]+paid[:\s£]+([\d,]+\.?\d*)",
        r"net payment[:\s£]+([\d,]+\.?\d*)",
        r"amount paid[:\s£]+([\d,]+\.?\d*)",
        r"net[:\s£]+([\d,]+\.?\d*)",
    ], text)

    found_fields = sum(x is not None for x in [contractor, period_start, period_end, gross, cis_deducted, net_paid])
    confidence: str
    if found_fields >= 5:
        confidence = "high"
    elif found_fields >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "contractor_name": contractor,
        "period_start": period_start,
        "period_end": period_end,
        "gross_total": gross,
        "materials_total": materials or 0.0,
        "cis_deducted_total": cis_deducted,
        "net_paid_total": net_paid,
        "ocr_confidence": confidence,
        "needs_review": confidence != "high",
    }


@app.post("/cis/statements/upload")
async def cis_upload_statement(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Accept a CIS statement file, attempt text extraction and OCR parsing.

    Returns parsed fields with confidence score. Always requires user review
    before creating a CIS record — caller must POST to /cis/records with confirmed data.
    """
    content_type = (file.content_type or "").lower()
    if not any(content_type.startswith(p) for p in _CIS_ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF or image files are accepted for CIS statement upload.",
        )

    raw = await file.read(_CIS_STATEMENT_MAX_BYTES + 1)
    if len(raw) > _CIS_STATEMENT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 10 MB limit.",
        )

    # Attempt text extraction
    text: str | None = None
    if content_type == "application/pdf" or file.filename and file.filename.lower().endswith(".pdf"):
        # Minimal PDF text extraction: scan for BT...ET blocks (works only for unencrypted PDFs)
        try:
            decoded = raw.decode("latin-1", errors="ignore")
            bt_blocks = re.findall(r"BT(.+?)ET", decoded, re.DOTALL)
            text_parts: list[str] = []
            for block in bt_blocks:
                tokens = re.findall(r"\(([^)]{1,200})\)", block)
                text_parts.extend(tokens)
            if text_parts:
                text = " ".join(text_parts)
        except Exception:
            text = None
    else:
        # Image — try UTF-8 decode (will fail for binary images, resulting in low confidence)
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            text = None

    document_id = str(uuid.uuid4())

    if not text or len(text.strip()) < 10:
        # Binary file with no extractable text — return empty fields, low confidence
        return {
            "document_id": document_id,
            "filename": file.filename,
            "contractor_name": None,
            "period_start": None,
            "period_end": None,
            "gross_total": None,
            "materials_total": 0.0,
            "cis_deducted_total": None,
            "net_paid_total": None,
            "ocr_confidence": "low",
            "needs_review": True,
            "note": "No text could be extracted from this file. Please fill in the fields manually.",
        }

    parsed = _parse_cis_statement_text(text)
    parsed["document_id"] = document_id
    parsed["filename"] = file.filename
    return parsed


@app.get("/cis/evidence-pack/manifest", response_model=schemas.EvidencePackManifestOut)
async def cis_evidence_manifest(
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
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
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CIS evidence pack is not included in your plan. Upgrade to Growth or higher.",
        )
    manifest = await crud_cis.build_evidence_manifest(
        db, user_id=user_id, tier=limits.evidence_pack_tier
    )
    return schemas.EvidencePackManifestOut(manifest=manifest)


@app.get("/cis/evidence-pack/zip")
async def cis_evidence_zip(
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
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
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CIS evidence pack export is not included in your plan. Upgrade to Growth or higher.",
        )
    manifest = await crud_cis.build_evidence_manifest(
        db, user_id=user_id, tier=limits.evidence_pack_tier
    )
    body = cis_evidence_share.zip_bytes_from_manifest(manifest)
    return StreamingResponse(
        iter([body]),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="mynettax-cis-evidence-pack.zip"'
        },
    )


@app.post(
    "/cis/evidence-pack/share-token",
    response_model=schemas.EvidenceShareTokenOut,
    status_code=status.HTTP_201_CREATED,
)
async def cis_evidence_share_token(
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    if limits.evidence_pack_tier == "none":
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="cis_evidence_pack_share",
            reason="evidence_tier_none",
            request_id=get_request_id(),
            extra={"tier": limits.evidence_pack_tier},
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CIS evidence pack export is not included in your plan. Upgrade to Growth or higher.",
        )
    ttl = int(os.getenv("CIS_EVIDENCE_SHARE_TOKEN_HOURS", "72"))
    token, exp_dt = cis_evidence_share.encode_share_token(
        user_id=user_id, tier=limits.evidence_pack_tier, ttl_hours=ttl
    )
    return schemas.EvidenceShareTokenOut(token=token, expires_at=exp_dt)


@app.get("/cis/evidence-pack/shared-zip")
async def cis_evidence_shared_zip(
    request: Request,
    token: str = Query(..., min_length=20),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = cis_evidence_share.decode_share_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired share link",
        ) from None
    user_id = str(payload["user_id"])
    tier = str(payload["tier"])
    manifest = await crud_cis.build_evidence_manifest(db, user_id=user_id, tier=tier)
    body = cis_evidence_share.zip_bytes_from_manifest(manifest)
    base = crud_cis.COMPLIANCE_SERVICE_URL
    if base:
        audit_jwt = _mint_short_lived_compliance_bearer(user_id)
        if audit_jwt:
            await post_audit_event(
                compliance_base_url=base,
                bearer_token=audit_jwt,
                user_id=user_id,
                action=CISAuditAction.CIS_EVIDENCE_PACK_SHARED_DOWNLOAD,
                details={
                    "share_jti": payload.get("jti"),
                    "tier": tier,
                    "client_host": request.client.host if request.client else None,
                },
            )
    return StreamingResponse(
        iter([body]),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="mynettax-cis-evidence-pack.zip"'
        },
    )


@app.get("/cis/evidence-pack/summary")
async def cis_evidence_pack_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Accountant-facing CIS evidence summary.
    Returns a structured overview of all CIS records for this user:
    total records, verification breakdown, amounts, and per-record status.
    Suitable for an accountant to review before completing SA returns.
    """
    from sqlalchemy import select as sa_select

    from app.models import CISRecord

    stmt = sa_select(CISRecord).where(CISRecord.user_id == user_id)
    rows = (await db.execute(stmt)).scalars().all()

    verified = [r for r in rows if r.evidence_status == "verified"]
    unverified = [r for r in rows if r.evidence_status != "verified"]

    total_verified_deducted = sum(float(r.cis_deducted_total or 0) for r in verified)
    total_unverified_deducted = sum(float(r.cis_deducted_total or 0) for r in unverified)
    total_gross = sum(float(r.gross_total or 0) for r in rows)

    records_out = [
        {
            "id": str(r.id),
            "contractor_name": r.contractor_name,
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "gross_total": float(r.gross_total or 0),
            "cis_deducted_total": float(r.cis_deducted_total or 0),
            "net_paid_total": float(r.net_paid_total or 0),
            "evidence_status": r.evidence_status,
            "reconciliation_status": r.reconciliation_status,
            "bank_net_observed_gbp": float(r.bank_net_observed_gbp or 0) if r.bank_net_observed_gbp is not None else None,
            "document_id": str(r.document_id) if r.document_id else None,
        }
        for r in sorted(rows, key=lambda x: (x.period_start or ""), reverse=True)
    ]

    return {
        "user_id": user_id,
        "total_records": len(rows),
        "verified_count": len(verified),
        "unverified_count": len(unverified),
        "total_gross_gbp": round(total_gross, 2),
        "total_verified_cis_deducted_gbp": round(total_verified_deducted, 2),
        "total_unverified_cis_deducted_gbp": round(total_unverified_deducted, 2),
        "total_cis_deducted_gbp": round(total_verified_deducted + total_unverified_deducted, 2),
        "not_advice_copy": (
            "This summary is prepared from records submitted by the client and "
            "has not been independently verified by MyNetTax. "
            "The accountant is responsible for confirming figures against CIS300 statements "
            "before inclusion in any HMRC return."
        ),
        "records": records_out,
    }


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
