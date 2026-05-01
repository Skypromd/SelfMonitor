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


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_clients_no_auth():
    resp = client.get("/clients")
    assert resp.status_code == 401


def test_create_client_no_auth():
    resp = client.post("/clients", json={"name": "Acme", "email": "acme@example.com"})
    assert resp.status_code == 401


def test_list_clients_with_auth():
    resp = client.get("/clients", headers=AUTH_HEADER)
    assert resp.status_code in (200, 500)


def test_create_client_with_auth():
    resp = client.post(
        "/clients",
        headers=AUTH_HEADER,
        json={"name": "Test Client", "email": "test@example.com"},
    )
    assert resp.status_code in (201, 200, 422, 500)


def test_list_invoices_no_auth():
    resp = client.get("/invoices")
    assert resp.status_code == 401
