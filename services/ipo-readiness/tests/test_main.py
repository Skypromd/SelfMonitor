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
    assert data["status"] == "building_unicorn_infrastructure"


def test_comprehensive_assessment_no_auth():
    resp = client.get("/assessment/comprehensive")
    assert resp.status_code == 401


def test_financial_readiness_no_auth():
    resp = client.get("/assessment/financial")
    assert resp.status_code == 401


def test_governance_board_no_auth():
    resp = client.get("/governance/board-composition")
    assert resp.status_code == 401


def test_comprehensive_assessment_with_auth():
    resp = client.get("/assessment/comprehensive", headers=AUTH_HEADER)
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert "overall_readiness_score" in data or "assessment_id" in data


def test_reporting_dashboard_with_auth():
    resp = client.get("/reporting/dashboard", headers=AUTH_HEADER)
    assert resp.status_code in (200, 503)


def test_investor_relations_dashboard_with_auth():
    resp = client.get("/investor-relations/dashboard", headers=AUTH_HEADER)
    assert resp.status_code in (200, 503)
