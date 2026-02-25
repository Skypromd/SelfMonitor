import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid

# Adjust path to import app and other modules
import sys
import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import get_db, Base
from app import schemas

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_AUTH_SECRET = "test-secret"
TEST_AUTH_ALGORITHM = "HS256"

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


def auth_headers(user_id: str = "fake-user-123") -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_import_and_get_transactions(db_session):
    account_id = str(uuid.uuid4())
    user_id = "fake-user-123"
    headers = auth_headers(user_id)

    # 1. Import transactions
    import_response = client.post(
        "/import",
        headers=headers,
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
    get_response = client.get(f"/accounts/{account_id}/transactions", headers=headers)
    assert get_response.status_code == 200
    transactions = get_response.json()
    assert len(transactions) == 2
    assert transactions[0]["description"] == "Salary" # Sorted by date desc
    assert transactions[1]["description"] == "Coffee"
    assert transactions[0]["user_id"] == user_id

@pytest.mark.asyncio
async def test_update_transaction_category(db_session):
    account_id = str(uuid.uuid4())
    headers = auth_headers()

    # 1. Import a transaction
    client.post(
        "/import",
        headers=headers,
        json={
            "account_id": account_id,
            "transactions": [
                {"provider_transaction_id": "txn-to-update", "date": "2023-10-05", "description": "Tesco", "amount": -55.0, "currency": "GBP"}
            ]
        }
    )

    # 2. Retrieve it to get its generated UUID
    get_response = client.get(f"/accounts/{account_id}/transactions", headers=headers)
    transaction_id = get_response.json()[0]["id"]

    # 3. Update its category
    update_response = client.patch(
        f"/transactions/{transaction_id}",
        headers=headers,
        json={"category": "groceries"}
    )
    assert update_response.status_code == 200
    updated_transaction = update_response.json()
    assert updated_transaction["category"] == "groceries"
    assert updated_transaction["description"] == "Tesco"

    # 4. Verify the update is persisted
    get_response_after_update = client.get(f"/accounts/{account_id}/transactions", headers=headers)
    assert get_response_after_update.json()[0]["category"] == "groceries"

@pytest.mark.asyncio
async def test_update_nonexistent_transaction(db_session):
    non_existent_id = str(uuid.uuid4())
    headers = auth_headers()
    response = client.patch(
        f"/transactions/{non_existent_id}",
        headers=headers,
        json={"category": "does-not-matter"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}

@pytest.mark.asyncio
async def test_get_all_my_transactions(db_session):
    headers = auth_headers()
    # Import transactions for two different accounts but for the same user
    account_id_1 = str(uuid.uuid4())
    account_id_2 = str(uuid.uuid4())

    client.post("/import", headers=headers, json={ "account_id": account_id_1, "transactions": [{"provider_transaction_id": "txn1", "date": "2023-10-01", "description": "Coffee", "amount": -5, "currency": "GBP"}]})
    client.post("/import", headers=headers, json={ "account_id": account_id_2, "transactions": [{"provider_transaction_id": "txn2", "date": "2023-10-02", "description": "Salary", "amount": 2500, "currency": "GBP"}]})

    # Call the new endpoint
    response = client.get("/transactions/me", headers=headers)

    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 2
    # Verify it returns transactions from both accounts
    descriptions = {t["description"] for t in transactions}
    assert "Coffee" in descriptions
    assert "Salary" in descriptions
