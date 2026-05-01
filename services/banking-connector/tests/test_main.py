import os
import sys

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def make_token(sub: str = "user-abc") -> str:
    payload = {"sub": sub, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


AUTH_HEADER = {"Authorization": f"Bearer {make_token()}"}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_initiate_connection_no_auth():
    resp = client.post(
        "/connections/initiate",
        json={"provider_id": "monzo", "redirect_uri": "https://localhost/callback"},
    )
    assert resp.status_code == 401


def test_callback_no_auth():
    resp = client.get("/connections/callback", params={"code": "abc123"})
    assert resp.status_code == 401


def test_initiate_connection_with_auth():
    resp = client.post(
        "/connections/initiate",
        headers=AUTH_HEADER,
        json={"provider_id": "monzo", "redirect_uri": "https://localhost/callback"},
    )
    assert resp.status_code in (200, 201, 422)
    if resp.status_code == 200:
        assert "consent_url" in resp.json()
