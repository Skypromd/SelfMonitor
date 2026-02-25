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

def test_fraud_risk_assessment_no_auth():
    resp = client.get("/fraud-risk-assessment/user1")
    assert resp.status_code == 401


def test_create_fraud_alert_no_auth():
    resp = client.post(
        "/fraud-alerts",
        params={
            "fraud_type": "transaction_fraud",
            "user_id": "u1",
            "risk_level": "high",
            "confidence_score": 0.9,
        },
    )
    assert resp.status_code == 401


def test_fraud_analytics_no_auth():
    resp = client.get("/fraud-analytics")
    assert resp.status_code == 401


def test_compliance_monitoring_no_auth():
    resp = client.get("/compliance-monitoring")
    assert resp.status_code == 401


def test_automated_compliance_check_no_auth():
    resp = client.post(
        "/automated-compliance-check",
        params={"user_id": "u1", "transaction_amount": 100.0},
    )
    assert resp.status_code == 401


def test_security_monetization_no_auth():
    resp = client.get("/security-monetization-metrics")
    assert resp.status_code == 401


# --- Authenticated endpoints ---

def test_fraud_risk_assessment():
    resp = client.get("/fraud-risk-assessment/user1", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user1"
    assert "fraud_score" in data
    assert "risk_level" in data
    assert data["status"] == "completed"


def test_create_fraud_alert():
    resp = client.post(
        "/fraud-alerts",
        params={
            "fraud_type": "transaction_fraud",
            "user_id": "user1",
            "risk_level": "high",
            "confidence_score": 0.9,
        },
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "alert_created" in data
    assert data["fraud_type"] == "transaction_fraud"
    assert data["estimated_loss_prevented"] > 0


def test_fraud_analytics():
    resp = client.get("/fraud-analytics", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "fraud_prevention_metrics" in data
    assert "fraud_types_breakdown" in data
    assert data["fraud_prevention_metrics"]["fraud_detection_accuracy"] > 0


def test_compliance_monitoring():
    resp = client.get("/compliance-monitoring", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "aml_compliance" in data
    assert "kyc_automation" in data
    assert "regulatory_monitoring" in data


def test_automated_compliance_check():
    resp = client.post(
        "/automated-compliance-check",
        params={"user_id": "user1", "transaction_amount": 500.0},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user1"
    assert "compliance_checks" in data
    assert data["status"] == "compliance_check_completed"


def test_security_monetization_metrics():
    resp = client.get("/security-monetization-metrics", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue_protection" in data
    assert "total_monetization_impact" in data
