"""Validation and auth behaviour without a live database."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_invoice_requires_auth():
    response = client.post("/invoices", json={})
    assert response.status_code == 401


def test_create_invoice_validation_empty_body_with_auth():
    # Invalid token still fails auth first (401)
    response = client.post(
        "/invoices",
        json={},
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == 401
