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
    assert data["status"] == "building_strategic_alliances"


def test_list_partners_no_auth():
    resp = client.get("/partners")
    assert resp.status_code == 401


def test_list_deals_no_auth():
    resp = client.get("/deals")
    assert resp.status_code == 401


def test_list_channel_programs_no_auth():
    resp = client.get("/channel-programs")
    assert resp.status_code == 401


def test_api_marketplace_no_auth():
    resp = client.get("/api-marketplace/products")
    assert resp.status_code == 401


def test_analytics_dashboard_no_auth():
    resp = client.get("/analytics/dashboard")
    assert resp.status_code == 401


def test_list_partners_with_auth():
    resp = client.get("/partners", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_analytics_dashboard_with_auth():
    resp = client.get("/analytics/dashboard", headers=AUTH_HEADER)
    assert resp.status_code == 200


def test_analytics_roi_with_auth():
    resp = client.get("/analytics/roi", headers=AUTH_HEADER)
    assert resp.status_code == 200
