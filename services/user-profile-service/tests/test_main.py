import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from jose import jwt

# Adjust path to import app and other modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import get_db, Base

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
async def test_create_and_get_profile(db_session):
    # Create profile
    response = client.put(
        "/profiles/me",
        headers=get_auth_headers(),
        json={"first_name": "Test", "last_name": "User", "date_of_birth": "2000-01-01"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["user_id"] == TEST_USER_ID

    # Get profile
    response = client.get("/profiles/me", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"

@pytest.mark.asyncio
async def test_update_profile(db_session):
    # Create profile first
    client.put("/profiles/me", headers=get_auth_headers(), json={"first_name": "Initial", "last_name": "Name"})

    # Update profile with a partial schema
    response = client.put("/profiles/me", headers=get_auth_headers(), json={"first_name": "Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name" # last_name should persist

@pytest.mark.asyncio
async def test_get_nonexistent_profile(db_session):
    response = client.get("/profiles/me", headers=get_auth_headers())
    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}
