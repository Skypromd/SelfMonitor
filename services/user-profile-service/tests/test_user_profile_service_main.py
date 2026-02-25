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
async def test_get_profile_found(db_session):
    """Test GET /profiles/me returns the profile when it exists."""
    headers = auth_headers("found-user")
    # Create the profile first
    client.put(
        "/profiles/me",
        headers=headers,
        json={"first_name": "Found", "last_name": "User", "date_of_birth": "1990-05-15"},
    )
    # Fetch it
    response = client.get("/profiles/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "found-user"
    assert data["first_name"] == "Found"
    assert data["last_name"] == "User"
    assert data["date_of_birth"] == "1990-05-15"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_profile_404_for_different_user(db_session):
    """GET /profiles/me returns 404 when the authenticated user has no profile."""
    headers = auth_headers("no-profile-user")
    response = client.get("/profiles/me", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_put_profile_creates_new(db_session):
    """PUT /profiles/me creates a new profile when none exists."""
    headers = auth_headers("new-user-1")
    response = client.put(
        "/profiles/me",
        headers=headers,
        json={"first_name": "New", "last_name": "Person"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "new-user-1"
    assert data["first_name"] == "New"
    assert data["last_name"] == "Person"


@pytest.mark.asyncio
async def test_put_profile_updates_existing(db_session):
    """PUT /profiles/me updates only the provided fields of an existing profile."""
    headers = auth_headers("update-user")
    # Create
    client.put(
        "/profiles/me",
        headers=headers,
        json={"first_name": "Original", "last_name": "Name", "date_of_birth": "1985-01-01"},
    )
    # Update only first_name
    response = client.put(
        "/profiles/me",
        headers=headers,
        json={"first_name": "Changed"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Changed"
    assert data["last_name"] == "Name"
    assert data["date_of_birth"] == "1985-01-01"


@pytest.mark.asyncio
async def test_get_profile_returns_401_without_token(db_session):
    """GET /profiles/me returns 401 when no auth token is provided."""
    response = client.get("/profiles/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_put_profile_returns_401_without_token(db_session):
    """PUT /profiles/me returns 401 when no auth token is provided."""
    response = client.put("/profiles/me", json={"first_name": "No Auth"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_returns_401_with_invalid_token(db_session):
    """GET /profiles/me returns 401 with an invalid JWT."""
    response = client.get(
        "/profiles/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(db_session):
    """GET /health returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
