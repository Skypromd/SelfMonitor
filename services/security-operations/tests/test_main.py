import os

os.environ["AUTH_SECRET_KEY"] = "test-secret"

import pytest
from app.main import app
from fastapi.testclient import TestClient
from jose import jwt

client = TestClient(app)

AUTH_SECRET_KEY = "test-secret"
AUTH_ALGORITHM = "HS256"


def make_token(sub: str = "test-user-123") -> str:
    return jwt.encode({"sub": sub}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


VALID_TOKEN = make_token()
AUTH_HEADER = {"Authorization": f"Bearer {VALID_TOKEN}"}

# SOC analyst and elevated clearance tokens
SOC_TOKEN = make_token(sub="soc_analyst_001")
SOC_HEADER = {"Authorization": f"Bearer {SOC_TOKEN}"}

ELEVATED_TOKEN = make_token(sub="elevated_user")
ELEVATED_HEADER = {"Authorization": f"Bearer {ELEVATED_TOKEN}"}


# --- Health check ---

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "secure"


# --- Auth required endpoints return 401 without token ---

def test_dashboard_no_auth():
    resp = client.get("/security/dashboard")
    assert resp.status_code == 401


def test_vulnerabilities_no_auth():
    resp = client.get("/security/vulnerabilities")
    assert resp.status_code == 401


def test_compliance_no_auth():
    resp = client.get("/security/compliance")
    assert resp.status_code == 401


def test_financial_impact_no_auth():
    resp = client.get("/security/financial-impact")
    assert resp.status_code == 401


def test_enterprise_readiness_no_auth():
    resp = client.get("/security/enterprise-readiness")
    assert resp.status_code == 401


def test_threat_detection_no_auth():
    resp = client.post("/security/threat-detection/analyze", json={"event_type": "login"})
    assert resp.status_code == 401


def test_create_incident_no_auth():
    resp = client.post("/security/incidents", json={
        "title": "Test incident",
        "description": "Test",
        "severity": "medium",
    })
    assert resp.status_code == 401


def test_encrypt_no_auth():
    resp = client.post("/security/encryption/encrypt", json={"data": "secret"})
    assert resp.status_code == 401


def test_zero_trust_no_auth():
    resp = client.post("/security/zero-trust/evaluate", json={
        "user_id": "u1",
        "resource": "db",
        "action": "read",
    })
    assert resp.status_code == 401


# --- Authenticated requests succeed ---

def test_dashboard_authenticated():
    # Dashboard requires soc_analyst clearance
    resp = client.get("/security/dashboard", headers=SOC_HEADER)
    assert resp.status_code == 200


def test_dashboard_basic_user_forbidden():
    resp = client.get("/security/dashboard", headers=AUTH_HEADER)
    assert resp.status_code == 403


def test_vulnerabilities_authenticated():
    resp = client.get("/security/vulnerabilities", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_compliance_authenticated():
    resp = client.get("/security/compliance", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_financial_impact_authenticated():
    resp = client.get("/security/financial-impact", headers=AUTH_HEADER)
    assert resp.status_code == 200


def test_enterprise_readiness_authenticated():
    resp = client.get("/security/enterprise-readiness", headers=AUTH_HEADER)
    assert resp.status_code == 200


def test_threat_detection_authenticated():
    resp = client.post(
        "/security/threat-detection/analyze",
        json={"event_type": "login_failure", "source_ip": "192.168.1.1"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200


def test_encrypt_authenticated():
    # Encrypt requires elevated clearance
    resp = client.post(
        "/security/encryption/encrypt",
        json={"data": "sensitive_value"},
        headers=ELEVATED_HEADER,
    )
    assert resp.status_code == 200
    assert "encrypted_data" in resp.json()


def test_encrypt_basic_user_forbidden():
    resp = client.post(
        "/security/encryption/encrypt",
        json={"data": "sensitive_value"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 403


def test_zero_trust_evaluate_authenticated():
    resp = client.post(
        "/security/zero-trust/evaluate",
        json={"user_id": "u1", "resource": "invoices_db", "action": "read"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
