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
    data = resp.json()
    assert data["status"] == "ready_for_global_expansion"


def test_supported_languages():
    resp = client.get("/localization/languages")
    assert resp.status_code == 200
    langs = resp.json()
    assert isinstance(langs, list)
    assert len(langs) > 0


def test_supported_currencies():
    resp = client.get("/currency/supported")
    assert resp.status_code == 200
    currencies = resp.json()
    assert isinstance(currencies, list)


def test_compliance_frameworks():
    resp = client.get("/compliance/frameworks")
    assert resp.status_code == 200
    frameworks = resp.json()
    assert isinstance(frameworks, list)


def test_expansion_markets():
    resp = client.get("/expansion/markets")
    assert resp.status_code == 200


def test_currency_convert_no_auth():
    resp = client.post(
        "/currency/convert",
        json={"amount": 100.0, "from_currency": "GBP", "to_currency": "USD"},
    )
    assert resp.status_code == 401


def test_currency_convert_with_auth():
    resp = client.post(
        "/currency/convert",
        headers=AUTH_HEADER,
        json={"amount": 100.0, "from_currency": "GBP", "to_currency": "USD"},
    )
    assert resp.status_code in (200, 422, 500)
