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


def auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_record_and_query_audit_events(db_session):
    user_1_headers = auth_headers("user_1")
    user_2_headers = auth_headers("user_2")

    # 1. Record an event for user_1
    response1 = client.post(
        "/audit-events",
        headers=user_1_headers,
        json={
            "user_id": "user_1",
            "action": "login.success",
            "details": {"ip_address": "127.0.0.1"}
        }
    )
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["user_id"] == "user_1"
    assert data1["action"] == "login.success"

    # 2. Record an event for user_2
    client.post(
        "/audit-events",
        headers=user_2_headers,
        json={"user_id": "user_2", "action": "profile.update"}
    )

    # 3. Query events for user_1
    response_query = client.get("/audit-events?user_id=user_1", headers=user_1_headers)
    assert response_query.status_code == 200
    query_data = response_query.json()
    assert len(query_data) == 1
    assert query_data[0]["action"] == "login.success"
    assert query_data[0]["user_id"] == "user_1"
    assert query_data[0]["details"]["ip_address"] == "127.0.0.1"

    # 4. Query all events
    response_all = client.get("/audit-events", headers=user_1_headers)
    assert response_all.status_code == 200
    assert len(response_all.json()) == 1


@pytest.mark.asyncio
async def test_query_for_other_user_is_forbidden(db_session):
    headers = auth_headers("user_1")
    response = client.get("/audit-events?user_id=user_2", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden user scope"
