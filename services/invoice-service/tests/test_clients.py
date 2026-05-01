"""
Tests for the /clients CRUD endpoints in invoice-service.

Uses in-memory SQLite so no real Postgres is required.
"""
import os
import sys
import types

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")

# ── Stub heavy optional deps not installed in the venv ────────────────────────
for _mod in ("weasyprint", "pandas", "openpyxl", "qrcode", "PIL",
             "redis", "aiofiles"):
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

_wp = sys.modules["weasyprint"]
_wp.HTML = object  # type: ignore[attr-defined]
_wp.CSS = object   # type: ignore[attr-defined]

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import MAX_CLIENTS_PER_USER  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# ── In-memory SQLite DB ────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

# ── Auth helper ────────────────────────────────────────────────────────────────
AUTH_SECRET = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "user-test-001"


def make_token(user_id: str = TEST_USER_ID) -> str:
    return jwt.encode({"sub": user_id}, AUTH_SECRET, algorithm=AUTH_ALGORITHM)


def auth_headers(user_id: str = TEST_USER_ID) -> dict:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_clients_empty(client):
    resp = await client.get("/clients", headers=auth_headers())
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_client(client):
    payload = {
        "name": "Acme Ltd",
        "email": "billing@acme.co.uk",
        "phone": "+44 20 1234 5678",
        "address": "1 High Street, London, EC1A 1AA",
        "vat_number": "GB123456789",
    }
    resp = await client.post("/clients", json=payload, headers=auth_headers())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Ltd"
    assert data["vat_number"] == "GB123456789"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_client(client):
    create_resp = await client.post(
        "/clients",
        json={"name": "Beta Corp"},
        headers=auth_headers(),
    )
    client_id = create_resp.json()["id"]

    resp = await client.get(f"/clients/{client_id}", headers=auth_headers())
    assert resp.status_code == 200
    assert resp.json()["name"] == "Beta Corp"


@pytest.mark.asyncio
async def test_update_client(client):
    create_resp = await client.post(
        "/clients",
        json={"name": "Old Name"},
        headers=auth_headers(),
    )
    client_id = create_resp.json()["id"]

    resp = await client.put(
        f"/clients/{client_id}",
        json={"name": "New Name", "phone": "+44 7700 900000"},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["phone"] == "+44 7700 900000"


@pytest.mark.asyncio
async def test_delete_client(client):
    create_resp = await client.post(
        "/clients",
        json={"name": "To Delete"},
        headers=auth_headers(),
    )
    client_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/clients/{client_id}", headers=auth_headers())
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/clients/{client_id}", headers=auth_headers())
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_client_limit_enforced(client):
    """User cannot create more than MAX_CLIENTS_PER_USER clients."""
    for i in range(MAX_CLIENTS_PER_USER):
        resp = await client.post(
            "/clients",
            json={"name": f"Client {i + 1}"},
            headers=auth_headers(),
        )
        assert resp.status_code == 201

    # 6th client must be rejected
    over_limit = await client.post(
        "/clients",
        json={"name": "One Too Many"},
        headers=auth_headers(),
    )
    assert over_limit.status_code == 422
    assert "limit" in over_limit.json()["detail"].lower()


@pytest.mark.asyncio
async def test_clients_are_user_isolated(client):
    """Clients of one user must not be visible to another user."""
    await client.post(
        "/clients",
        json={"name": "User A Client"},
        headers=auth_headers("user-a"),
    )

    resp = await client.get("/clients", headers=auth_headers("user-b"))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_nonexistent_client_returns_404(client):
    import uuid
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/clients/{fake_id}", headers=auth_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/clients")
    assert resp.status_code == 401
