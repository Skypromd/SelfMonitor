from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import csv
import io
import hashlib
import datetime

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
    imported_count, skipped_count = await crud.create_transactions(
        db, 
        user_id=user_id, 
        account_id=request.account_id, 
        transactions=request.transactions
    )
    return {"message": "Import request accepted", "imported_count": imported_count, "skipped_count": skipped_count}


@app.post("/ingest/partner", response_model=schemas.IngestionResult, status_code=status.HTTP_202_ACCEPTED)
async def ingest_partner_batch(
    request: schemas.PartnerIngestionRequest,
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts a partner batch payload following the data contract and imports transactions.
    """
    imported_count, skipped_count = await crud.create_transactions(
        db,
        user_id=user_id,
        account_id=request.account_id,
        transactions=request.transactions
    )
    return schemas.IngestionResult(
        message="Partner batch accepted",
        imported_count=imported_count,
        skipped_count=skipped_count
    )


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _get_first_value(row: dict, keys: List[str]) -> str | None:
    for key in keys:
        normalized_key = _normalize_header(key)
        if normalized_key in row and row[normalized_key] not in (None, ""):
            return str(row[normalized_key]).strip()
    return None


def _parse_date(value: str) -> datetime.date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("Unsupported date format.")


def _parse_amount(value: str) -> float:
    cleaned = value.strip().replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    return float(cleaned)


def _generate_provider_id(base: str) -> str:
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]


@app.post("/import/csv", response_model=schemas.IngestionResult, status_code=status.HTTP_202_ACCEPTED)
async def import_transactions_csv(
    account_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db),
):
    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is required.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8 encoded.")

    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.get_dialect("excel")

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV header row is required.")

    normalized_rows = []
    for row in reader:
        normalized_rows.append({_normalize_header(k): v for k, v in row.items()})

    valid_transactions: List[schemas.TransactionBase] = []
    invalid_count = 0
    for idx, row in enumerate(normalized_rows, start=1):
        try:
            date_value = _get_first_value(row, ["date", "transaction_date", "posted_date"])
            description = _get_first_value(row, ["description", "merchant", "narrative", "details"])
            amount_value = _get_first_value(row, ["amount", "value"])
            currency = _get_first_value(row, ["currency", "currency_code", "iso_currency"])

            if not date_value or not description or not amount_value or not currency:
                raise ValueError("Missing required fields.")

            parsed_date = _parse_date(date_value)
            parsed_amount = _parse_amount(amount_value)
            parsed_currency = currency.upper()

            provider_transaction_id = _get_first_value(
                row, ["provider_transaction_id", "transaction_id", "id"]
            )
            if not provider_transaction_id:
                base = f"{parsed_date}|{description}|{parsed_amount}|{parsed_currency}|{idx}"
                provider_transaction_id = _generate_provider_id(base)

            tax_category = _get_first_value(row, ["tax_category"])
            category = _get_first_value(row, ["category"])
            business_use_percent = _get_first_value(row, ["business_use_percent", "business_use_pct"])
            parsed_business_use = float(business_use_percent) if business_use_percent else None

            valid_transactions.append(
                schemas.TransactionBase(
                    provider_transaction_id=provider_transaction_id,
                    date=parsed_date,
                    description=description,
                    amount=parsed_amount,
                    currency=parsed_currency,
                    category=category,
                    tax_category=tax_category,
                    business_use_percent=parsed_business_use,
                )
            )
        except Exception:
            invalid_count += 1

    if not valid_transactions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid transactions found.")

    imported_count, skipped_count = await crud.create_transactions(
        db,
        user_id=user_id,
        account_id=account_id,
        transactions=valid_transactions,
    )

    return schemas.IngestionResult(
        message="CSV import accepted",
        imported_count=imported_count,
        skipped_count=skipped_count + invalid_count,
    )

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
