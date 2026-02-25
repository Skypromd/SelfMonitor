import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Adjust path to import app and other modules
import sys
import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)

from app.main import app
from app.database import get_db, Base

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
async def test_create_and_get_profile(db_session):
    headers = auth_headers()
    # Create profile
    response = client.put(
        "/profiles/me",
        headers=headers,
        json={"first_name": "Test", "last_name": "User", "date_of_birth": "2000-01-01"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["user_id"] == "fake-user-123"

    # Get profile
    response = client.get("/profiles/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"

@pytest.mark.asyncio
async def test_update_profile(db_session):
    headers = auth_headers()
    # Create profile first
    client.put("/profiles/me", headers=headers, json={"first_name": "Initial", "last_name": "Name"})

    # Update profile with a partial schema
    response = client.put("/profiles/me", headers=headers, json={"first_name": "Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name" # last_name should persist

@pytest.mark.asyncio
async def test_get_nonexistent_profile(db_session):
    response = client.get("/profiles/me", headers=auth_headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


@pytest.mark.asyncio
async def test_subscription_defaults(db_session):
    response = client.get("/subscriptions/me")
    assert response.status_code == 200
    data = response.json()
    assert data["subscription_plan"] == "free"
    assert data["subscription_status"] == "active"
    assert data["billing_cycle"] == "monthly"


@pytest.mark.asyncio
async def test_update_subscription(db_session):
    response = client.put(
        "/subscriptions/me",
        json={
            "subscription_plan": "pro",
            "subscription_status": "active",
            "monthly_close_day": 5
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subscription_plan"] == "pro"
    assert data["monthly_close_day"] == 5
