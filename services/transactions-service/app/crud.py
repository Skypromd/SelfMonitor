from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import uuid
from typing import List
import httpx
import os
import asyncio

CATEGORIZATION_SERVICE_URL = os.getenv("CATEGORIZATION_SERVICE_URL", "http://localhost:8013/categorize")

async def get_suggested_category(description: str, auth_token: str) -> str | None:
    """Calls the categorization service to get a suggested category."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CATEGORIZATION_SERVICE_URL,
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"description": description},
                timeout=2.0,
            )
            if response.status_code == 200:
                return response.json().get("category")
    except httpx.RequestError:
        # If the service is down or fails, we just don't categorize.
        return None
    return None

async def create_transactions(
    db: AsyncSession,
    user_id: str,
    account_id: uuid.UUID,
    transactions: List[schemas.TransactionBase],
    auth_token: str,
):
    """
    Creates multiple transaction records, enriching them with categories from the categorization service.
    """
    # Create categorization tasks for all transactions concurrently
    category_tasks = [get_suggested_category(t.description, auth_token) for t in transactions]
    suggested_categories = await asyncio.gather(*category_tasks)

    db_transactions = []
    for t, category in zip(transactions, suggested_categories):
        db_transactions.append(
            models.Transaction(
                user_id=user_id,
                account_id=account_id,
                category=category, # Add the suggested category
                **t.dict()
            )
        )

    db.add_all(db_transactions)
    await db.commit()
    return len(db_transactions)

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
