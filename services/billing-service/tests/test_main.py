"""Tests for billing-service."""
import os

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")

import pytest
from app.main import _upsert_subscription, app, init_db
from fastapi.testclient import TestClient

# Ensure DB tables exist before any test runs
init_db()

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "dev_mode" in data


def test_list_plans():
    resp = client.get("/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert "starter" in data
    assert "growth" in data
    assert "pro" in data
    assert "business" in data
    assert data["starter"]["amount"] == 900
    assert data["pro"]["amount"] == 1500


def test_checkout_free_plan():
    resp = client.post("/checkout/session", json={"plan": "free"})
    assert resp.status_code == 200
    data = resp.json()
    # Free plan skips payment
    assert "/register" in data["checkout_url"]
    assert data["session_id"] == "free"


def test_checkout_paid_plan_dev_mode():
    resp = client.post("/checkout/session", json={"plan": "starter", "email": "test@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    # In dev mode (no STRIPE_SECRET_KEY), should redirect to checkout-success
    assert data["dev_mode"] is True
    assert "checkout-success" in data["checkout_url"] or "/register" in data["checkout_url"]
    assert data["session_id"].startswith("dev_session_")


def test_checkout_unknown_plan():
    resp = client.post("/checkout/session", json={"plan": "unknown_plan_xyz"})
    assert resp.status_code == 400


def test_subscription_not_found():
    resp = client.get("/subscription/nobody@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["status"] == "none"


def test_subscription_upsert_and_read(tmp_path):
    import app.main as billing_main
    old_db = billing_main.DB_PATH
    billing_main.DB_PATH = str(tmp_path / "test_billing.db")
    init_db()

    _upsert_subscription(
        email="user@example.com",
        plan="starter",
        status="trialing",
        stripe_session_id="cs_test_123",
    )

    resp = client.get("/subscription/user@example.com")
    # Client uses the patched DB path
    assert resp.status_code == 200
    billing_main.DB_PATH = old_db


def test_webhook_ignored_without_secret():
    resp = client.post("/webhook", content=b"not json")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_checkout_completed(tmp_path):
    import json

    import app.main as billing_main
    old_db = billing_main.DB_PATH
    billing_main.DB_PATH = str(tmp_path / "webhook_test.db")
    init_db()

    payload = json.dumps({
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc",
                "customer_email": "webhook@example.com",
                "customer": "cus_abc",
                "subscription": "sub_abc",
                "metadata": {"plan": "pro"},
                "customer_details": {"email": "webhook@example.com"},
            }
        }
    }).encode()

    resp = client.post("/webhook", content=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    billing_main.DB_PATH = old_db
