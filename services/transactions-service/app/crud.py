from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import uuid
from typing import List
import httpx
import os
import asyncio

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

async def create_transactions(db: AsyncSession, user_id: str, account_id: uuid.UUID, transactions: List[schemas.TransactionBase]):
    """
    Creates multiple transaction records, enriching them with categories from the categorization service.
    """
    # Create categorization tasks for all transactions concurrently
    category_tasks = [get_suggested_category(t.description) for t in transactions]
    suggested_categories = await asyncio.gather(*category_tasks)

    db_transactions = []
    for t, category in zip(transactions, suggested_categories):
        db_transactions.append(
            models.Transaction(
                user_id=user_id,
                account_id=account_id,
                category=category, # Add the suggested category
                **t.model_dump()
            )
        )

    db.add_all(db_transactions)
    await db.commit()
    return len(db_transactions)


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
