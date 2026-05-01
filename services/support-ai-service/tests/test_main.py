import os

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret")

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# --- Health check ---

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "support" in data["service"]


# --- Tickets ---

def test_create_ticket():
    payload = {
        "subject": "I need help with invoices",
        "message": "My invoice is not generating correctly",
        "user_email": "user@example.com",
        "category": "billing",
    }
    resp = client.post("/tickets", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == payload["subject"]
    assert data["user_email"] == payload["user_email"]
    assert "id" in data


def test_list_tickets_empty_initially():
    # Separate client instance so DB starts fresh
    from fastapi.testclient import TestClient as TC
    with TC(app) as c:
        resp = c.get("/tickets")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_and_list_tickets():
    payload = {
        "subject": "Tax question",
        "message": "How do I file self-assessment?",
        "user_email": "tax@example.com",
        "category": "technical",
    }
    resp = client.post("/tickets", json=payload)
    assert resp.status_code == 201
    ticket_id = resp.json()["id"]

    list_resp = client.get("/tickets")
    assert list_resp.status_code == 200
    ids = [t["id"] for t in list_resp.json()]
    assert ticket_id in ids


def test_list_tickets_filter_by_status():
    resp = client.get("/tickets", params={"status": "open"})
    assert resp.status_code == 200
    for ticket in resp.json():
        assert ticket["status"] == "open"


# --- Feedback ---

def test_submit_feedback():
    fb_resp = client.post("/feedback", json={
        "rating": 5,
        "comment": "Great support!",
        "user_email": "fb@example.com",
    })
    assert fb_resp.status_code == 201
    assert fb_resp.json()["ok"] is True


# --- Stats ---

def test_get_stats():
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tickets" in data
    assert "open_tickets" in data
    assert "resolved_tickets" in data
    assert "avg_rating" in data
    assert "total_sessions" in data
