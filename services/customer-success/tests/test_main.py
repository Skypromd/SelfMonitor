import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"

from unittest.mock import patch, AsyncMock

import pytest
from jose import jwt
from fastapi.testclient import TestClient

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


# --- Auth required endpoints return 401 without token ---

def test_user_journey_no_auth():
    resp = client.get("/user-journey/user1")
    assert resp.status_code == 401


def test_proactive_intervention_no_auth():
    resp = client.post("/proactive-intervention", params={"user_id": "u1"})
    assert resp.status_code == 401


def test_success_metrics_no_auth():
    resp = client.get("/success-metrics/user1")
    assert resp.status_code == 401


def test_cohort_analysis_no_auth():
    resp = client.get("/cohort-analysis")
    assert resp.status_code == 401


def test_automated_campaign_no_auth():
    resp = client.post("/automated-success-campaigns/weekly_value_reminder")
    assert resp.status_code == 401


# --- Authenticated endpoints ---

def test_get_user_journey():
    resp = client.get("/user-journey/user1", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user1"
    assert "current_stage" in data
    assert "churn_risk" in data


def test_proactive_intervention():
    resp = client.post(
        "/proactive-intervention",
        params={"user_id": "user1"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "interventions_triggered" in data


def test_success_metrics():
    resp = client.get("/success-metrics/user1", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_active_days" in data
    assert "features_adopted" in data


def test_cohort_analysis():
    resp = client.get("/cohort-analysis", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "cohorts" in data
    assert "success_program_impact" in data


def test_automated_campaign_valid():
    resp = client.post(
        "/automated-success-campaigns/weekly_value_reminder",
        params={"target_segment": "active_users"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_launched"] == "weekly_value_reminder"


def test_automated_campaign_not_found():
    resp = client.post(
        "/automated-success-campaigns/nonexistent_campaign",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 404
