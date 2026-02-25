import asyncio
import datetime
import os
import uuid
from typing import List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models, schemas

CATEGORIZATION_SERVICE_URL = os.getenv("CATEGORIZATION_SERVICE_URL", "http://localhost:8013/categorize")
RECEIPT_DRAFT_ACCOUNT_NAMESPACE = uuid.UUID(
    os.getenv("RECEIPT_DRAFT_ACCOUNT_NAMESPACE", "f0b6e53b-0dd0-4f65-91d2-7bb272f8ea20")
)
RECEIPT_DRAFT_PREFIX = "receipt-draft-"

async def get_suggested_category(description: str) -> str | None:
    """Calls the categorization service to get a suggested category."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(CATEGORIZATION_SERVICE_URL, json={"description": description}, timeout=2.0)
            if response.status_code == 200:
                return response.json().get("category")
    except httpx.RequestError:
        # If the service is down or fails, we just don't categorize.
        return None
    return None


def _extract_receipt_draft_vendor(description: str) -> str | None:
    prefix = "Receipt draft:"
    if not description.startswith(prefix):
        return None

    tail = description[len(prefix) :].strip()
    vendor = tail.split("(", 1)[0].strip()
    return vendor.lower() if vendor else None


def _is_receipt_draft(transaction: models.Transaction) -> bool:
    return bool(transaction.provider_transaction_id and transaction.provider_transaction_id.startswith(RECEIPT_DRAFT_PREFIX))


def _ignored_candidate_id_set(transaction: models.Transaction) -> set[str]:
    raw = transaction.ignored_candidate_ids
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if str(item)}


def _set_ignored_candidate_ids(transaction: models.Transaction, values: set[str]) -> None:
    transaction.ignored_candidate_ids = sorted(values)


def _candidate_confidence_score(
    draft_transaction: models.Transaction,
    candidate_transaction: models.Transaction,
) -> float:
    amount_gap = abs(abs(float(draft_transaction.amount)) - abs(float(candidate_transaction.amount)))
    if amount_gap > 1.0:
        return 0.0
    day_gap = abs((candidate_transaction.date - draft_transaction.date).days)
    if day_gap > 14:
        return 0.0

    amount_score = 1.0 - min(amount_gap, 1.0)
    date_score = 1.0 - (day_gap / 14.0)
    vendor_bonus = 0.0
    draft_vendor = _extract_receipt_draft_vendor(draft_transaction.description)
    if draft_vendor and draft_vendor in candidate_transaction.description.lower():
        vendor_bonus = 0.2

    return round((amount_score * 0.6) + (date_score * 0.2) + vendor_bonus, 3)


async def _list_non_draft_candidates_for_receipt(
    db: AsyncSession,
    *,
    user_id: str,
    draft_transaction: models.Transaction,
    candidate_limit: int,
    include_ignored: bool = False,
    search_provider_transaction_id: str | None = None,
    search_amount: float | None = None,
    search_date: datetime.date | None = None,
) -> list[schemas.ReceiptDraftCandidate]:
    manual_filter_mode = any(
        (
            search_provider_transaction_id,
            search_amount is not None,
            search_date is not None,
        )
    )
    start_date = draft_transaction.date - datetime.timedelta(days=14)
    end_date = draft_transaction.date + datetime.timedelta(days=14)

    query = (
        select(models.Transaction)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.id != draft_transaction.id,
            models.Transaction.provider_transaction_id.not_like(f"{RECEIPT_DRAFT_PREFIX}%"),
            models.Transaction.currency == draft_transaction.currency,
        )
        .order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
    )
    if search_date:
        query = query.filter(models.Transaction.date == search_date)
    else:
        query = query.filter(
            models.Transaction.date >= start_date,
            models.Transaction.date <= end_date,
        )
    if search_provider_transaction_id:
        query = query.filter(models.Transaction.provider_transaction_id.ilike(f"%{search_provider_transaction_id}%"))

    result = await db.execute(query)
    candidates = list(result.scalars().all())
    ignored_ids = _ignored_candidate_id_set(draft_transaction)

    scored_candidates: list[schemas.ReceiptDraftCandidate] = []
    for candidate in candidates:
        if search_amount is not None and abs(abs(float(candidate.amount)) - abs(float(search_amount))) > 0.01:
            continue

        ignored = str(candidate.id) in ignored_ids
        if ignored and not include_ignored:
            continue

        confidence = _candidate_confidence_score(draft_transaction, candidate)
        if confidence <= 0 and not manual_filter_mode:
            continue
        if confidence <= 0 and manual_filter_mode:
            confidence = 0.01
        scored_candidates.append(
            schemas.ReceiptDraftCandidate(
                transaction_id=candidate.id,
                account_id=candidate.account_id,
                provider_transaction_id=candidate.provider_transaction_id,
                date=candidate.date,
                description=candidate.description,
                amount=candidate.amount,
                currency=candidate.currency,
                category=candidate.category,
                confidence_score=confidence,
                ignored=ignored,
            )
        )

    scored_candidates.sort(key=lambda item: item.confidence_score, reverse=True)
    return scored_candidates[:candidate_limit]


async def _find_matching_receipt_draft(
    db: AsyncSession,
    *,
    user_id: str,
    imported_transaction: schemas.TransactionBase,
) -> models.Transaction | None:
    start_date = imported_transaction.date - datetime.timedelta(days=3)
    end_date = imported_transaction.date + datetime.timedelta(days=3)
    result = await db.execute(
        select(models.Transaction)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.provider_transaction_id.like(f"{RECEIPT_DRAFT_PREFIX}%"),
            (models.Transaction.reconciliation_status != "ignored") | (models.Transaction.reconciliation_status.is_(None)),
            models.Transaction.currency == imported_transaction.currency.upper(),
            models.Transaction.date >= start_date,
            models.Transaction.date <= end_date,
        )
        .order_by(models.Transaction.date.desc())
    )
    candidates = list(result.scalars().all())
    imported_description = imported_transaction.description.lower()

    for candidate in candidates:
        if abs(abs(candidate.amount) - abs(imported_transaction.amount)) > 0.01:
            continue

        draft_vendor = _extract_receipt_draft_vendor(candidate.description)
        if draft_vendor and draft_vendor not in imported_description:
            continue
        return candidate
    return None


def _reconcile_receipt_draft_with_imported_transaction(
    receipt_draft: models.Transaction,
    *,
    account_id: uuid.UUID,
    imported_transaction: schemas.TransactionBase,
    suggested_category: str | None,
) -> None:
    receipt_draft.account_id = account_id
    receipt_draft.provider_transaction_id = imported_transaction.provider_transaction_id
    receipt_draft.date = imported_transaction.date
    receipt_draft.description = imported_transaction.description
    receipt_draft.amount = imported_transaction.amount
    receipt_draft.currency = imported_transaction.currency.upper()
    receipt_draft.reconciliation_status = None
    receipt_draft.ignored_candidate_ids = None
    if not receipt_draft.category:
        receipt_draft.category = suggested_category


async def create_transactions(
    db: AsyncSession,
    user_id: str,
    account_id: uuid.UUID,
    transactions: List[schemas.TransactionBase],
) -> dict[str, int]:
    """
    Imports bank transactions while auto-reconciling matching receipt draft entries.
    """
    stats = {
        "imported_count": 0,
        "created_count": 0,
        "reconciled_receipt_drafts": 0,
        "skipped_duplicates": 0,
    }

    category_tasks = [get_suggested_category(t.description) for t in transactions]
    suggested_categories = await asyncio.gather(*category_tasks)

    for t, category in zip(transactions, suggested_categories):
        existing_result = await db.execute(
            select(models.Transaction).filter(
                models.Transaction.user_id == user_id,
                models.Transaction.provider_transaction_id == t.provider_transaction_id,
            )
        )
        if existing_result.scalars().first():
            stats["skipped_duplicates"] += 1
            continue

        matching_receipt_draft = await _find_matching_receipt_draft(
            db,
            user_id=user_id,
            imported_transaction=t,
        )
        if matching_receipt_draft:
            _reconcile_receipt_draft_with_imported_transaction(
                matching_receipt_draft,
                account_id=account_id,
                imported_transaction=t,
                suggested_category=category,
            )
            stats["reconciled_receipt_drafts"] += 1
            stats["imported_count"] += 1
            continue

        db.add(
            models.Transaction(
                user_id=user_id,
                account_id=account_id,
                provider_transaction_id=t.provider_transaction_id,
                date=t.date,
                description=t.description,
                amount=t.amount,
                currency=t.currency.upper(),
                category=category,
            )
        )
        stats["created_count"] += 1
        stats["imported_count"] += 1

    if stats["created_count"] > 0 or stats["reconciled_receipt_drafts"] > 0:
        await db.commit()
    return stats


def _receipt_draft_account_id(user_id: str) -> uuid.UUID:
    return uuid.uuid5(RECEIPT_DRAFT_ACCOUNT_NAMESPACE, user_id)


def _build_receipt_draft_description(payload: schemas.ReceiptDraftCreateRequest) -> str:
    title = payload.vendor_name or payload.filename
    if payload.expense_article:
        return f"Receipt draft: {title} ({payload.expense_article})"
    return f"Receipt draft: {title}"


async def create_or_get_receipt_draft_transaction(
    db: AsyncSession,
    *,
    user_id: str,
    payload: schemas.ReceiptDraftCreateRequest,
) -> tuple[models.Transaction, bool]:
    provider_transaction_id = f"{RECEIPT_DRAFT_PREFIX}{payload.document_id}"
    existing = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.provider_transaction_id == provider_transaction_id,
        )
    )
    existing_transaction = existing.scalars().first()
    if existing_transaction:
        return existing_transaction, True

    category = payload.suggested_category
    if not category:
        category = await get_suggested_category(payload.vendor_name or payload.filename)

    db_transaction = models.Transaction(
        user_id=user_id,
        account_id=_receipt_draft_account_id(user_id),
        provider_transaction_id=provider_transaction_id,
        date=payload.transaction_date,
        description=_build_receipt_draft_description(payload),
        amount=-abs(payload.total_amount),
        currency=payload.currency.upper(),
        category=category,
        reconciliation_status="open",
        ignored_candidate_ids=[],
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction, False


async def list_unmatched_receipt_drafts(
    db: AsyncSession,
    *,
    user_id: str,
    limit: int = 25,
    offset: int = 0,
    candidate_limit: int = 5,
    include_ignored: bool = False,
    search_provider_transaction_id: str | None = None,
    search_amount: float | None = None,
    search_date: datetime.date | None = None,
) -> tuple[int, list[schemas.UnmatchedReceiptDraftItem]]:
    query = (
        select(models.Transaction)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.provider_transaction_id.like(f"{RECEIPT_DRAFT_PREFIX}%"),
        )
        .order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
    )
    if not include_ignored:
        query = query.filter(
            (models.Transaction.reconciliation_status != "ignored") | (models.Transaction.reconciliation_status.is_(None))
        )
    result = await db.execute(query)
    all_drafts = list(result.scalars().all())
    total = len(all_drafts)
    page_drafts = all_drafts[offset : offset + limit]

    items: list[schemas.UnmatchedReceiptDraftItem] = []
    for draft_transaction in page_drafts:
        candidates = await _list_non_draft_candidates_for_receipt(
            db,
            user_id=user_id,
            draft_transaction=draft_transaction,
            candidate_limit=candidate_limit,
            include_ignored=include_ignored,
            search_provider_transaction_id=search_provider_transaction_id,
            search_amount=search_amount,
            search_date=search_date,
        )
        items.append(
            schemas.UnmatchedReceiptDraftItem(
                draft_transaction=draft_transaction,
                candidates=candidates,
            )
        )
    return total, items


async def get_receipt_draft_candidates(
    db: AsyncSession,
    *,
    user_id: str,
    draft_transaction_id: uuid.UUID,
    limit: int = 20,
    include_ignored: bool = True,
    search_provider_transaction_id: str | None = None,
    search_amount: float | None = None,
    search_date: datetime.date | None = None,
) -> tuple[models.Transaction, list[schemas.ReceiptDraftCandidate]]:
    draft_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.id == draft_transaction_id,
            models.Transaction.user_id == user_id,
        )
    )
    draft_transaction = draft_result.scalars().first()
    if not draft_transaction or not _is_receipt_draft(draft_transaction):
        raise ValueError("draft_not_found")

    candidates = await _list_non_draft_candidates_for_receipt(
        db,
        user_id=user_id,
        draft_transaction=draft_transaction,
        candidate_limit=limit,
        include_ignored=include_ignored,
        search_provider_transaction_id=search_provider_transaction_id,
        search_amount=search_amount,
        search_date=search_date,
    )
    return draft_transaction, candidates


async def ignore_receipt_draft_candidate(
    db: AsyncSession,
    *,
    user_id: str,
    draft_transaction_id: uuid.UUID,
    target_transaction_id: uuid.UUID,
) -> models.Transaction:
    draft_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.id == draft_transaction_id,
            models.Transaction.user_id == user_id,
        )
    )
    draft_transaction = draft_result.scalars().first()
    if not draft_transaction:
        raise ValueError("draft_not_found")
    if not _is_receipt_draft(draft_transaction):
        raise ValueError("draft_not_unmatched")

    target_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.id == target_transaction_id,
            models.Transaction.user_id == user_id,
        )
    )
    target_transaction = target_result.scalars().first()
    if not target_transaction:
        raise ValueError("target_not_found")
    if _is_receipt_draft(target_transaction):
        raise ValueError("target_is_draft")

    ignored_ids = _ignored_candidate_id_set(draft_transaction)
    ignored_ids.add(str(target_transaction_id))
    _set_ignored_candidate_ids(draft_transaction, ignored_ids)
    if draft_transaction.reconciliation_status is None:
        draft_transaction.reconciliation_status = "open"
    await db.commit()
    await db.refresh(draft_transaction)
    return draft_transaction


async def set_receipt_draft_status(
    db: AsyncSession,
    *,
    user_id: str,
    draft_transaction_id: uuid.UUID,
    status: str,
) -> models.Transaction:
    if status not in {"open", "ignored"}:
        raise ValueError("invalid_status")

    draft_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.id == draft_transaction_id,
            models.Transaction.user_id == user_id,
        )
    )
    draft_transaction = draft_result.scalars().first()
    if not draft_transaction:
        raise ValueError("draft_not_found")
    if not _is_receipt_draft(draft_transaction):
        raise ValueError("draft_not_unmatched")

    draft_transaction.reconciliation_status = status
    if status == "open" and draft_transaction.ignored_candidate_ids is None:
        draft_transaction.ignored_candidate_ids = []
    await db.commit()
    await db.refresh(draft_transaction)
    return draft_transaction


async def manual_reconcile_receipt_draft(
    db: AsyncSession,
    *,
    user_id: str,
    draft_transaction_id: uuid.UUID,
    target_transaction_id: uuid.UUID,
) -> tuple[models.Transaction, uuid.UUID]:
    draft_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.id == draft_transaction_id,
            models.Transaction.user_id == user_id,
        )
    )
    draft_transaction = draft_result.scalars().first()
    if not draft_transaction:
        raise ValueError("draft_not_found")
    if not _is_receipt_draft(draft_transaction):
        raise ValueError("draft_not_unmatched")

    target_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.id == target_transaction_id,
            models.Transaction.user_id == user_id,
        )
    )
    target_transaction = target_result.scalars().first()
    if not target_transaction:
        raise ValueError("target_not_found")
    if _is_receipt_draft(target_transaction):
        raise ValueError("target_is_draft")

    conflict_result = await db.execute(
        select(models.Transaction).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.provider_transaction_id == target_transaction.provider_transaction_id,
            models.Transaction.id != draft_transaction.id,
            models.Transaction.id != target_transaction.id,
        )
    )
    if conflict_result.scalars().first():
        raise ValueError("target_provider_conflict")

    preserved_category = draft_transaction.category or target_transaction.category
    draft_transaction.account_id = target_transaction.account_id
    draft_transaction.provider_transaction_id = target_transaction.provider_transaction_id
    draft_transaction.date = target_transaction.date
    draft_transaction.description = target_transaction.description
    draft_transaction.amount = target_transaction.amount
    draft_transaction.currency = target_transaction.currency
    draft_transaction.category = preserved_category
    draft_transaction.reconciliation_status = None
    draft_transaction.ignored_candidate_ids = None

    removed_id = target_transaction.id
    await db.delete(target_transaction)
    await db.commit()
    await db.refresh(draft_transaction)
    return draft_transaction, removed_id

async def get_transactions_by_account(db: AsyncSession, user_id: str, account_id: uuid.UUID):
    """Fetches all transactions for a specific account belonging to a user."""
    result = await db.execute(
        select(models.Transaction)
        .filter(models.Transaction.user_id == user_id, models.Transaction.account_id == account_id)
        .order_by(models.Transaction.date.desc())
    )
    return result.scalars().all()

async def get_transactions_by_user(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 50):
    """Fetches all transactions for a specific user across all their accounts."""
    result = await db.execute(
        select(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .order_by(models.Transaction.date.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def update_transaction(db: AsyncSession, user_id: str, transaction_id: uuid.UUID, update_request: schemas.TransactionUpdateRequest):
    """Updates the category/tax fields of a single transaction."""
    result = await db.execute(
        select(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == user_id)
    )
    db_transaction = result.scalars().first()

    if db_transaction:
        if update_request.category is not None:
            db_transaction.category = update_request.category
        if update_request.tax_category is not None:
            db_transaction.tax_category = update_request.tax_category
        if update_request.business_use_percent is not None:
            db_transaction.business_use_percent = update_request.business_use_percent
        await db.commit()
        await db.refresh(db_transaction)

    return db_transaction
