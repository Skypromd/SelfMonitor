from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from . import crud, models, schemas
from .database import get_db
from .telemetry import setup_telemetry

app = FastAPI(
    title="Transactions Service",
    description="Stores and categorizes financial transactions.",
    version="1.0.0"
)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

# --- Placeholder Security ---
def fake_auth_check() -> str:
    """A fake dependency to simulate user authentication and return a user ID."""
    return "fake-user-123"

# --- Endpoints ---
@app.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_transactions(
    request: schemas.TransactionImportRequest, 
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """Imports a batch of transactions for an account into the database."""
    imported_count = await crud.create_transactions(
        db, 
        user_id=user_id, 
        account_id=request.account_id, 
        transactions=request.transactions
    )
    return {"message": "Import request accepted", "imported_count": imported_count}

@app.get("/accounts/{account_id}/transactions", response_model=List[schemas.Transaction])
async def get_transactions_for_account(
    account_id: uuid.UUID, 
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for a specific account belonging to the user from the database."""
    transactions = await crud.get_transactions_by_account(db, user_id=user_id, account_id=account_id)
    return transactions

@app.get("/transactions/me", response_model=List[schemas.Transaction])
async def get_all_my_transactions(
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all transactions for the authenticated user across all accounts."""
    transactions = await crud.get_transactions_by_user(db, user_id=user_id)
    return transactions

@app.patch("/transactions/{transaction_id}", response_model=schemas.Transaction)
async def update_transaction(
    transaction_id: uuid.UUID,
    update_request: schemas.TransactionUpdateRequest,
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """Updates the category/tax fields of a single transaction in the database."""
    if (
        update_request.category is None
        and update_request.tax_category is None
        and update_request.business_use_percent is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    updated_transaction = await crud.update_transaction(
        db, 
        user_id=user_id, 
        transaction_id=transaction_id, 
        update_request=update_request
    )
    if not updated_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return updated_transaction
