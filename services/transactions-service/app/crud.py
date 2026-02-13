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
            models.Transaction.provider_transaction_id.like("receipt-draft-%"),
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
    provider_transaction_id = f"receipt-draft-{payload.document_id}"
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
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction, False

async def get_transactions_by_account(db: AsyncSession, user_id: str, account_id: uuid.UUID):
    """Fetches all transactions for a specific account belonging to a user."""
    result = await db.execute(
        select(models.Transaction)
        .filter(models.Transaction.user_id == user_id, models.Transaction.account_id == account_id)
        .order_by(models.Transaction.date.desc())
    )
    return result.scalars().all()

async def get_transactions_by_user(db: AsyncSession, user_id: str):
    """Fetches all transactions for a specific user across all their accounts."""
    result = await db.execute(
        select(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .order_by(models.Transaction.date.desc())
    )
    return result.scalars().all()

async def update_transaction_category(db: AsyncSession, user_id: str, transaction_id: uuid.UUID, category: str):
    """Updates the category of a single transaction."""
    result = await db.execute(
        select(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == user_id)
    )
    db_transaction = result.scalars().first()

    if db_transaction:
        db_transaction.category = category
        await db.commit()
        await db.refresh(db_transaction)

    return db_transaction
