import os
import sys
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, get_db
from app.main import app

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


def test_record_consent_triggers_audit(mocker):
    mock_log_audit = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock)
    connection_id = str(uuid.uuid4())

    response = client.post(
        "/consents",
        headers=get_auth_headers(),
        json={
            "connection_id": connection_id,
            "provider": "test_bank",
            "scopes": ["accounts", "transactions"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "test_bank"
    assert payload["status"] == "active"

    mock_log_audit.assert_awaited_once()
    call_args = mock_log_audit.call_args.kwargs
    assert call_args["action"] == "consent.granted"
    assert call_args["details"]["provider"] == "test_bank"
    assert call_args["details"]["scopes"] == ["accounts", "transactions"]


def test_revoke_consent_triggers_audit(mocker):
    mock_log_audit = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock)
    create_response = client.post(
        "/consents",
        headers=get_auth_headers(),
        json={
            "connection_id": str(uuid.uuid4()),
            "provider": "test_bank",
            "scopes": ["transactions"],
        },
    )
    assert create_response.status_code == 201
    consent_id = create_response.json()["id"]
    mock_log_audit.reset_mock()

    revoke_response = client.delete(f"/consents/{consent_id}", headers=get_auth_headers())
    assert revoke_response.status_code == 204

    mock_log_audit.assert_awaited_once()
    call_args = mock_log_audit.call_args.kwargs
    assert call_args["user_id"] == TEST_USER_ID
    assert call_args["action"] == "consent.revoked"
    assert call_args["details"]["consent_id"] == consent_id

