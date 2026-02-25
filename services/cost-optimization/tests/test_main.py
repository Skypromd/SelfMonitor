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

def test_cost_analysis_no_auth():
    resp = client.get("/cost-analysis")
    assert resp.status_code == 401


def test_implement_optimization_no_auth():
    resp = client.post("/implement-optimization/auto_scaling")
    assert resp.status_code == 401


def test_cost_efficiency_no_auth():
    resp = client.get("/cost-efficiency-metrics")
    assert resp.status_code == 401


def test_automation_recommendations_no_auth():
    resp = client.get("/automation-recommendations")
    assert resp.status_code == 401


def test_deploy_full_optimization_no_auth():
    resp = client.post("/deploy-full-optimization")
    assert resp.status_code == 401


def test_optimization_dashboard_no_auth():
    resp = client.get("/optimization-dashboard")
    assert resp.status_code == 401


# --- Authenticated endpoints ---

def test_cost_analysis():
    resp = client.get("/cost-analysis", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "current_costs" in data
    assert "optimization_opportunities" in data
    assert "savings_summary" in data
    assert data["current_costs"]["total_monthly"] > 0


def test_implement_optimization_valid():
    resp = client.post("/implement-optimization/auto_scaling", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["optimization_started"] == "auto_scaling"
    assert "expected_monthly_savings" in data


def test_implement_optimization_not_found():
    resp = client.post("/implement-optimization/nonexistent", headers=AUTH_HEADER)
    assert resp.status_code == 404


def test_cost_efficiency_metrics():
    resp = client.get("/cost-efficiency-metrics", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "current_metrics" in data
    assert "optimization_targets" in data
    assert "automation_impact" in data


def test_automation_recommendations():
    resp = client.get("/automation-recommendations", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "high_impact_automations" in data
    assert data["total_additional_savings_potential"] > 0


def test_deploy_full_optimization():
    resp = client.post("/deploy-full-optimization", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["comprehensive_optimization_initiated"] is True
    assert "optimization_plan" in data


def test_optimization_dashboard():
    resp = client.get("/optimization-dashboard", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "cost_optimization_summary" in data
    assert "financial_impact" in data
