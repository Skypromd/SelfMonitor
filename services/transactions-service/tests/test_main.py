import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid
from jose import jwt

# Adjust path to import app and other modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import get_db, Base
from app import schemas

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Fixture to create/drop tables for each test function
@pytest_asyncio.fixture()
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
    user_id = TEST_USER_ID

    # 1. Import transactions
    import_response = client.post(
        "/import",
        headers=get_auth_headers(user_id),
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

    # 2. Get transactions for that account
    get_response = client.get(f"/accounts/{account_id}/transactions", headers=get_auth_headers(user_id))
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
        headers=get_auth_headers(),
        json={
            "account_id": account_id,
            "transactions": [
                {"provider_transaction_id": "txn-to-update", "date": "2023-10-05", "description": "Tesco", "amount": -55.0, "currency": "GBP"}
            ]
        }
    )

    # 2. Retrieve it to get its generated UUID
    get_response = client.get(f"/accounts/{account_id}/transactions", headers=get_auth_headers())
    transaction_id = get_response.json()[0]["id"]

    # 3. Update its category
    update_response = client.patch(
        f"/transactions/{transaction_id}",
        headers=get_auth_headers(),
        json={"category": "groceries"}
    )
    assert update_response.status_code == 200
    updated_transaction = update_response.json()
    assert updated_transaction["category"] == "groceries"
    assert updated_transaction["description"] == "Tesco"

    # 4. Verify the update is persisted
    get_response_after_update = client.get(f"/accounts/{account_id}/transactions", headers=get_auth_headers())
    assert get_response_after_update.json()[0]["category"] == "groceries"

@pytest.mark.asyncio
async def test_update_nonexistent_transaction(db_session):
    non_existent_id = str(uuid.uuid4())
    response = client.patch(
        f"/transactions/{non_existent_id}",
        headers=get_auth_headers(),
        json={"category": "does-not-matter"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}

@pytest.mark.asyncio
async def test_get_all_my_transactions(db_session):
    # Import transactions for two different accounts but for the same user
    account_id_1 = str(uuid.uuid4())
    account_id_2 = str(uuid.uuid4())

    client.post("/import", headers=get_auth_headers(), json={ "account_id": account_id_1, "transactions": [{"provider_transaction_id": "txn1", "date": "2023-10-01", "description": "Coffee", "amount": -5, "currency": "GBP"}]})
    client.post("/import", headers=get_auth_headers(), json={ "account_id": account_id_2, "transactions": [{"provider_transaction_id": "txn2", "date": "2023-10-02", "description": "Salary", "amount": 2500, "currency": "GBP"}]})

    # Call the new endpoint
    response = client.get("/transactions/me", headers=get_auth_headers())

    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 2
    # Verify it returns transactions from both accounts
    descriptions = {t["description"] for t in transactions}
    assert "Coffee" in descriptions
    assert "Salary" in descriptions


@pytest.mark.asyncio
async def test_create_receipt_draft_transaction_and_deduplicate(db_session):
    payload = {
        "document_id": str(uuid.uuid4()),
        "filename": "trainline_receipt.pdf",
        "transaction_date": "2026-02-12",
        "total_amount": 28.45,
        "currency": "GBP",
        "vendor_name": "Trainline",
        "suggested_category": "transport",
        "expense_article": "travel_costs",
        "is_potentially_deductible": True,
    }

    first_response = client.post(
        "/transactions/receipt-drafts",
        headers=get_auth_headers(),
        json=payload,
    )
    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["duplicated"] is False
    first_tx = first_data["transaction"]
    assert first_tx["provider_transaction_id"].startswith("receipt-draft-")
    assert first_tx["amount"] == -28.45
    assert first_tx["category"] == "transport"
    assert "Receipt draft: Trainline" in first_tx["description"]

    second_response = client.post(
        "/transactions/receipt-drafts",
        headers=get_auth_headers(),
        json=payload,
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["duplicated"] is True
    assert second_data["transaction"]["id"] == first_tx["id"]
