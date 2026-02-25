import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"

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

def test_churn_prediction_no_auth():
    resp = client.get("/churn-prediction/user1")
    assert resp.status_code == 401


def test_cohort_churn_analysis_no_auth():
    resp = client.get("/cohort-churn-analysis")
    assert resp.status_code == 401


def test_intervention_campaign_no_auth():
    resp = client.post("/intervention-campaigns/reactivation_email")
    assert resp.status_code == 401


def test_ml_model_performance_no_auth():
    resp = client.get("/ml-model-performance")
    assert resp.status_code == 401


# --- Authenticated endpoints ---

def test_churn_prediction():
    resp = client.get("/churn-prediction/user1", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user1"
    assert "churn_probability" in data
    assert "risk_level" in data
    assert "key_risk_factors" in data
    assert "recommended_interventions" in data
    assert 0 <= data["churn_probability"] <= 1.0


def test_cohort_churn_analysis():
    resp = client.get("/cohort-churn-analysis", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "cohort_month" in data
    assert "churn_by_month" in data
    assert "predictive_insights" in data


def test_intervention_campaign_valid():
    resp = client.post(
        "/intervention-campaigns/reactivation_email",
        params={"target_risk_level": "high"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_launched"] == "reactivation_email"
    assert "targeting" in data


def test_intervention_campaign_not_found():
    resp = client.post(
        "/intervention-campaigns/nonexistent",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 404


def test_ml_model_performance():
    resp = client.get("/ml-model-performance", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "model_metrics" in data
    assert "business_impact" in data
    assert data["model_metrics"]["accuracy"] > 0
