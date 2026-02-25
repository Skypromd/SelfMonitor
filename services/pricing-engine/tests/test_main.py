import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"

from unittest.mock import patch, MagicMock

import pytest
from jose import jwt
from fastapi.testclient import TestClient

mock_redis = MagicMock()
mock_redis.hgetall.return_value = {}
mock_redis.hincrby.return_value = 1
mock_redis.expire.return_value = True

with patch("redis.from_url", return_value=mock_redis):
    from app.main import app

client = TestClient(app)

AUTH_SECRET_KEY = "test-secret"
AUTH_ALGORITHM = "HS256"


def make_token(sub: str = "test-user-123") -> str:
    return jwt.encode({"sub": sub}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


VALID_TOKEN = make_token()
AUTH_HEADER = {"Authorization": f"Bearer {VALID_TOKEN}"}


# --- Health check ---

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Public endpoints ---

def test_get_pricing_plans():
    resp = client.get("/pricing-plans")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    tiers = [p["tier"] for p in data]
    assert "free" in tiers
    assert "enterprise" in tiers


# --- Auth required endpoints return 401 without token ---

def test_usage_no_auth():
    resp = client.get("/usage/user1")
    assert resp.status_code == 401


def test_track_usage_no_auth():
    resp = client.post("/track-usage", params={"user_id": "u1", "metric": "api_calls"})
    assert resp.status_code == 401


def test_pricing_recommendation_no_auth():
    resp = client.get("/pricing-recommendation/user1")
    assert resp.status_code == 401


def test_dynamic_pricing_no_auth():
    resp = client.get("/dynamic-pricing/user1", params={"target_tier": "pro"})
    assert resp.status_code == 401


def test_pricing_analytics_no_auth():
    resp = client.get("/pricing-analytics")
    assert resp.status_code == 401


# --- Authenticated endpoints ---

def test_get_usage():
    resp = client.get("/usage/user1", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user1"
    assert "current_tier" in data
    assert "usage_this_month" in data


def test_track_usage():
    resp = client.post(
        "/track-usage",
        params={"user_id": "user1", "metric": "api_calls", "quantity": 1},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "api_calls"
    assert "new_total" in data


def test_pricing_recommendation():
    resp = client.get("/pricing-recommendation/user1", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended_tier" in data
    assert "confidence_score" in data


def test_dynamic_pricing():
    resp = client.get(
        "/dynamic-pricing/user1",
        params={"target_tier": "starter"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "base_price" in data
    assert "personalized_price" in data
    assert "discount_percent" in data


def test_pricing_analytics():
    resp = client.get("/pricing-analytics", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "conversion_rates" in data
    assert "revenue_optimization" in data
