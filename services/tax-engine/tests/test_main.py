import os
import sys

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def make_token(sub: str = "user-abc") -> str:
    payload = {
        "sub": sub,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


AUTH_HEADER = {"Authorization": f"Bearer {make_token()}"}


def test_metrics_no_auth():
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_calculate_no_auth():
    resp = client.post(
        "/calculate",
        json={"start_date": "2025-04-06", "end_date": "2026-04-05", "jurisdiction": "UK"},
    )
    assert resp.status_code == 401


def test_calculate_and_submit_no_auth():
    resp = client.post(
        "/calculate-and-submit",
        json={"start_date": "2025-04-06", "end_date": "2026-04-05", "jurisdiction": "UK"},
    )
    assert resp.status_code == 401


def test_calculate_invalid_dates():
    resp = client.post(
        "/calculate",
        headers=AUTH_HEADER,
        json={"start_date": "2026-04-05", "end_date": "2025-04-06", "jurisdiction": "UK"},
    )
    assert resp.status_code == 400


def test_calculate_unsupported_jurisdiction():
    resp = client.post(
        "/calculate",
        headers=AUTH_HEADER,
        json={"start_date": "2025-04-06", "end_date": "2026-04-05", "jurisdiction": "US"},
    )
    assert resp.status_code == 400


def test_calculate_with_mocked_transactions():
    mock_transactions = [
        {"date": "2025-06-01", "amount": 5000.0, "category": "income"},
        {"date": "2025-07-01", "amount": 200.0, "category": "transport"},
    ]
    with patch("app.main.get_json_with_retry", new=AsyncMock(return_value=mock_transactions)):
        resp = client.post(
            "/calculate",
            headers=AUTH_HEADER,
            json={"start_date": "2025-04-06", "end_date": "2026-04-05", "jurisdiction": "UK"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "estimated_tax_due" in data
    assert data["user_id"] == "user-abc"
