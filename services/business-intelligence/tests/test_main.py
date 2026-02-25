import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"

import fastapi.routing

_original_init = fastapi.routing.APIRoute.__init__


def _safe_route_init(self, *args, **kwargs):
    try:
        _original_init(self, *args, **kwargs)
    except fastapi.exceptions.FastAPIError:
        kwargs.setdefault("response_model", None)
        endpoint = args[1] if len(args) > 1 else kwargs.get("endpoint")
        if endpoint:
            import inspect
            sig = inspect.signature(endpoint)
            new_params = []
            for p in sig.parameters.values():
                from fastapi import BackgroundTasks
                ann = p.annotation
                origin = getattr(ann, "__origin__", None)
                args_ = getattr(ann, "__args__", ())
                if origin is type(None) or (args_ and BackgroundTasks in args_):
                    continue
                if ann is BackgroundTasks or p.name == "background_tasks":
                    continue
                new_params.append(p)
            endpoint.__signature__ = sig.replace(parameters=new_params)
            if len(args) > 1:
                args = (args[0], endpoint, *args[2:])
            else:
                kwargs["endpoint"] = endpoint
        _original_init(self, *args, **kwargs)


fastapi.routing.APIRoute.__init__ = _safe_route_init

from app.main import app  # noqa: E402

fastapi.routing.APIRoute.__init__ = _original_init

import pytest  # noqa: E402
from jose import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

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

def test_revenue_intelligence_no_auth():
    resp = client.get("/revenue-intelligence")
    assert resp.status_code == 401


def test_customer_intelligence_no_auth():
    resp = client.get("/customer-intelligence")
    assert resp.status_code == 401


def test_market_intelligence_no_auth():
    resp = client.get("/market-intelligence")
    assert resp.status_code == 401


def test_data_monetization_no_auth():
    resp = client.get("/data-monetization-analytics")
    assert resp.status_code == 401


def test_generate_insights_no_auth():
    resp = client.post(
        "/generate-business-insights",
        params={"analysis_type": "revenue_optimization"},
    )
    assert resp.status_code == 401


def test_executive_dashboard_no_auth():
    resp = client.get("/executive-dashboard")
    assert resp.status_code == 401


# --- Authenticated endpoints ---

def test_revenue_intelligence():
    resp = client.get("/revenue-intelligence", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue_overview" in data
    assert "revenue_streams_analysis" in data
    assert "predictive_analytics" in data
    assert data["revenue_overview"]["total_revenue"] > 0


def test_customer_intelligence():
    resp = client.get("/customer-intelligence", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "customer_segmentation" in data
    assert "behavior_patterns" in data
    assert "monetization_insights" in data


def test_market_intelligence():
    resp = client.get("/market-intelligence", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "market_trends" in data
    assert "competitive_landscape" in data
    assert "opportunity_analysis" in data


def test_data_monetization_analytics():
    resp = client.get("/data-monetization-analytics", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "data_assets_valuation" in data
    assert "analytics_as_a_service" in data
    assert "total_data_monetization_potential" in data


def test_generate_business_insights():
    resp = client.post(
        "/generate-business-insights",
        params={"analysis_type": "revenue_optimization"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_type"] == "revenue_optimization"
    assert "insights" in data
    assert data["insights_generated"] > 0


def test_executive_dashboard():
    resp = client.get("/executive-dashboard", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "key_performance_indicators" in data
    assert "growth_metrics" in data
    assert "strategic_opportunities" in data
    assert "financial_health" in data
