import datetime
import sys
import uuid
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db
from .telemetry import setup_telemetry

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

app = FastAPI(
    title="Transactions Service",
    description="Stores and categorizes financial transactions.",
    version="1.0.0"
)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

# --- Endpoints ---
@app.post(
    "/import",
    response_model=schemas.TransactionImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_transactions(
    request: schemas.TransactionImportRequest, 
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Imports a batch of transactions for an account into the database."""
    import_result = await crud.create_transactions(
        db, 
        user_id=user_id, 
        account_id=request.account_id, 
        transactions=request.transactions,
        auth_token=auth_token,
    )
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
    updated_transaction = await crud.update_transaction_category(
        db, 
        user_id=user_id, 
        transaction_id=transaction_id, 
        category=update_request.category
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


@app.post("/transactions/receipt-drafts", response_model=schemas.ReceiptDraftCreateResponse)
async def create_receipt_draft_transaction(
    payload: schemas.ReceiptDraftCreateRequest,
    user_id: str = Depends(get_current_user_id),
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
