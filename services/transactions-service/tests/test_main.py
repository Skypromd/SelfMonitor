import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid

# Adjust path to import app and other modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import get_db, Base
from app import schemas

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Fixture to create/drop tables for each test function
@pytest.fixture()
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# --- Tests ---
client = TestClient(app)

@pytest.mark.asyncio
async def test_import_and_get_transactions(db_session):
    account_id = str(uuid.uuid4())
    user_id = "fake-user-123" # This comes from fake_auth_check

    # 1. Import transactions
    import_response = client.post(
        "/import",
        json={
            "account_id": account_id,
            "transactions": [
                {"provider_transaction_id": "txn1", "date": "2023-10-01", "description": "Coffee", "amount": -4.5, "currency": "GBP"},
                {"provider_transaction_id": "txn2", "date": "2023-10-02", "description": "Salary", "amount": 2500.0, "currency": "GBP"},
            ]
        }
    )
    assert import_response.status_code == 202
    assert import_response.json()["imported_count"] == 2
    assert import_response.json()["skipped_count"] == 0

    # 2. Get transactions for that account
    get_response = client.get(f"/accounts/{account_id}/transactions")
    assert get_response.status_code == 200
    transactions = get_response.json()
    assert len(transactions) == 2
    assert transactions[0]["description"] == "Salary" # Sorted by date desc
    assert transactions[1]["description"] == "Coffee"
    assert transactions[0]["user_id"] == user_id

@pytest.mark.asyncio
async def test_update_transaction_category(db_session):
    account_id = str(uuid.uuid4())

    # 1. Import a transaction
    client.post(
        "/import",
        json={
            "account_id": account_id,
            "transactions": [
                {"provider_transaction_id": "txn-to-update", "date": "2023-10-05", "description": "Tesco", "amount": -55.0, "currency": "GBP"}
            ]
        }
    )

    # 2. Retrieve it to get its generated UUID
    get_response = client.get(f"/accounts/{account_id}/transactions")
    transaction_id = get_response.json()[0]["id"]

    # 3. Update its category
    update_response = client.patch(
        f"/transactions/{transaction_id}",
        json={"category": "groceries"}
    )
    assert update_response.status_code == 200
    updated_transaction = update_response.json()
    assert updated_transaction["category"] == "groceries"
    assert updated_transaction["description"] == "Tesco"

    # 4. Update tax fields
    update_tax_response = client.patch(
        f"/transactions/{transaction_id}",
        json={"tax_category": "travel", "business_use_percent": 80}
    )
    assert update_tax_response.status_code == 200
    updated_tax = update_tax_response.json()
    assert updated_tax["tax_category"] == "travel"
    assert updated_tax["business_use_percent"] == 80.0

    # 5. Verify the updates are persisted
    get_response_after_update = client.get(f"/accounts/{account_id}/transactions")
    fetched = get_response_after_update.json()[0]
    assert fetched["category"] == "groceries"
    assert fetched["tax_category"] == "travel"
    assert fetched["business_use_percent"] == 80.0

@pytest.mark.asyncio
async def test_update_nonexistent_transaction(db_session):
    non_existent_id = str(uuid.uuid4())
    response = client.patch(
        f"/transactions/{non_existent_id}",
        json={"category": "does-not-matter"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}

@pytest.mark.asyncio
async def test_get_all_my_transactions(db_session):
    # Import transactions for two different accounts but for the same user
    account_id_1 = str(uuid.uuid4())
    account_id_2 = str(uuid.uuid4())

    client.post("/import", json={ "account_id": account_id_1, "transactions": [{"provider_transaction_id": "txn1", "date": "2023-10-01", "description": "Coffee", "amount": -5, "currency": "GBP"}]})
    client.post("/import", json={ "account_id": account_id_2, "transactions": [{"provider_transaction_id": "txn2", "date": "2023-10-02", "description": "Salary", "amount": 2500, "currency": "GBP"}]})

    # Call the new endpoint
    response = client.get("/transactions/me")

    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 2
    # Verify it returns transactions from both accounts
    descriptions = {t["description"] for t in transactions}
    assert "Coffee" in descriptions
    assert "Salary" in descriptions


@pytest.mark.asyncio
async def test_import_csv_transactions(db_session):
    account_id = str(uuid.uuid4())
    csv_content = (
        "date,description,amount,currency\n"
        "2023-10-01,Coffee,-3.50,GBP\n"
        "2023-10-02,Salary,2500,GBP\n"
    )

    response = client.post(
        "/import/csv",
        data={"account_id": account_id},
        files={"file": ("transactions.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 202
    assert response.json()["imported_count"] == 2
    assert response.json()["skipped_count"] == 0

    repeat_response = client.post(
        "/import/csv",
        data={"account_id": account_id},
        files={"file": ("transactions.csv", csv_content, "text/csv")},
    )
    assert repeat_response.status_code == 202
    assert repeat_response.json()["imported_count"] == 0
    assert repeat_response.json()["skipped_count"] == 2


@pytest.mark.asyncio
async def test_import_deduplicates_by_provider_id(db_session):
    account_id = str(uuid.uuid4())

    payload = {
        "account_id": account_id,
        "transactions": [
            {"provider_transaction_id": "dup-1", "date": "2023-10-01", "description": "Coffee", "amount": -4.5, "currency": "GBP"}
        ]
    }

    first_response = client.post("/import", json=payload)
    assert first_response.status_code == 202
    assert first_response.json()["imported_count"] == 1
    assert first_response.json()["skipped_count"] == 0

    second_response = client.post("/import", json=payload)
    assert second_response.status_code == 202
    assert second_response.json()["imported_count"] == 0
    assert second_response.json()["skipped_count"] == 1


@pytest.mark.asyncio
async def test_partner_ingestion_endpoint(db_session):
    account_id = str(uuid.uuid4())
    payload = {
        "schema_version": "1.0",
        "source_system": "partner-app",
        "user_reference": "partner-user-42",
        "account_id": account_id,
        "transactions": [
            {"provider_transaction_id": "p-1", "date": "2023-10-01", "description": "Invoice", "amount": 1500.0, "currency": "GBP"}
        ]
    }

    response = client.post("/ingest/partner", json=payload)
    assert response.status_code == 202
    assert response.json()["imported_count"] == 1
    assert response.json()["skipped_count"] == 0
