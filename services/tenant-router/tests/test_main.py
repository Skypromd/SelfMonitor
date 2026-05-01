import os

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Patch asyncpg and redis before importing app to avoid connection attempts
with patch("asyncpg.create_pool", new=AsyncMock(return_value=MagicMock())):
    with patch("redis.asyncio.from_url", return_value=MagicMock()):
        from app.main import app

client = TestClient(app)


# --- Shards status (no external deps) ---

def test_shards_status():
    resp = client.get("/shards/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "shards" in data
    assert "total_shards" in data
    assert data["total_shards"] >= 0


# --- Tenant endpoints ---

def test_get_tenant_database_url_unknown_tenant():
    """Unknown tenant should return an error (500 or 503)."""
    resp = client.get("/tenant/nonexistent-tenant/database-url")
    assert resp.status_code in (500, 503, 404)


def test_get_tenant_health():
    """Tenant health returns a response (200 with real infra, 503 without)."""
    resp = client.get("/tenant/test-tenant/health")
    assert resp.status_code in (200, 503)


# --- With mocked TenantRouter ---

def test_tenant_database_url_with_mock():
    with patch("app.main.tenant_router") as mock_router:
        mock_router.get_tenant_database_url = AsyncMock(
            return_value="postgresql://user:pass@shard1/db_test_tenant"
        )
        resp = client.get("/tenant/test-tenant/database-url")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "test-tenant"
    assert "database_url" in data


def test_tenant_health_with_mock():
    with patch("app.main.tenant_router") as mock_router:
        mock_router.get_tenant_health = AsyncMock(return_value={
            "status": "healthy",
            "tenant_id": "test-tenant",
            "shard": "shard_1",
        })
        resp = client.get("/tenant/test-tenant/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
