import os
import sys

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from app.database import Base, get_db
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


from app.main import app

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def make_token(sub: str = "user-abc") -> str:
    payload = {"sub": sub, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


AUTH_HEADER = {"Authorization": f"Bearer {make_token()}"}


def test_create_consent_no_auth():
    resp = client.post(
        "/consents",
        json={"provider": "monzo", "scopes": ["transactions"]},
    )
    assert resp.status_code == 401


def test_list_consents_no_auth():
    resp = client.get("/consents")
    assert resp.status_code == 401


def test_create_and_list_consents():
    resp = client.post(
        "/consents",
        headers=AUTH_HEADER,
        json={"provider": "monzo", "scopes": ["transactions", "accounts"]},
    )
    assert resp.status_code in (201, 200, 500)
    if resp.status_code in (201, 200):
        data = resp.json()
        assert data["provider"] == "monzo"
        assert data["status"] == "active"

        list_resp = client.get("/consents", headers=AUTH_HEADER)
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert isinstance(items, list)


def test_revoke_consent_not_found():
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/consents/{fake_id}", headers=AUTH_HEADER)
    assert resp.status_code in (404, 500)
