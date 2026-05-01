import os
import sys

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "SelfMonitor Recommendation Engine"
    assert data["status"] == "operational"


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
