from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import uuid
from typing import List
import httpx
import os
import asyncio

CATEGORIZATION_SERVICE_URL = os.getenv("CATEGORIZATION_SERVICE_URL", "http://localhost:8013/categorize")

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
    Skips any transactions that already exist for the same account and provider_transaction_id.
    """
    if not transactions:
        return 0, 0

    provider_ids = [t.provider_transaction_id for t in transactions]
    result = await db.execute(
        select(models.Transaction.provider_transaction_id)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.account_id == account_id,
            models.Transaction.provider_transaction_id.in_(provider_ids),
        )
    )
    existing_ids = {row[0] for row in result.all()}
    new_transactions = [t for t in transactions if t.provider_transaction_id not in existing_ids]

    if not new_transactions:
        return 0, len(transactions)

    category_tasks = [get_suggested_category(t.description) for t in new_transactions]
    suggested_categories = await asyncio.gather(*category_tasks)

    db_transactions = []
    for t, category in zip(new_transactions, suggested_categories):
        db_transactions.append(
            models.Transaction(
                user_id=user_id,
                account_id=account_id,
                category=category,
                **t.model_dump()
            )
        )

    db.add_all(db_transactions)
    await db.commit()
    return len(db_transactions), len(transactions) - len(db_transactions)

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
