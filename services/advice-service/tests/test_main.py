import datetime
import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["AUTH_SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app, AUTH_SECRET_KEY, AUTH_ALGORITHM

client = TestClient(app)


def _make_token(sub: str = "user-123") -> str:
    return jwt.encode({"sub": sub}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


AUTH_HEADER = {"Authorization": f"Bearer {_make_token()}"}


def _mock_httpx_context(transactions):
    """Return an AsyncMock that acts as ``async with httpx.AsyncClient() as c``."""
    mock_response = MagicMock()
    mock_response.json.return_value = transactions
    mock_response.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    return mock_client_instance


# --- Health endpoint ---

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Auth: missing / invalid token ---

def test_generate_returns_401_without_token():
    response = client.post("/generate", json={"topic": "spending_analysis"})
    assert response.status_code == 401


def test_generate_returns_401_with_invalid_token():
    response = client.post(
        "/generate",
        json={"topic": "spending_analysis"},
        headers={"Authorization": "Bearer bad-token"},
    )
    assert response.status_code == 401


# --- Validation: invalid topic ---

def test_generate_rejects_invalid_topic():
    response = client.post(
        "/generate",
        json={"topic": "nonexistent_topic"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 422


# --- income_protection ---

@patch("app.main.httpx.AsyncClient")
def test_income_protection_with_data(mock_async_client_cls):
    today = datetime.date.today()
    transactions = [
        {"date": (today - datetime.timedelta(days=30 * i)).isoformat(), "amount": 3000.0, "description": "Salary"}
        for i in range(6)
    ]
    mock_async_client_cls.return_value = _mock_httpx_context(transactions)

    response = client.post(
        "/generate",
        json={"topic": "income_protection"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "income_protection"
    assert "£3,000/month" in data["headline"]


@patch("app.main.httpx.AsyncClient")
def test_income_protection_no_data(mock_async_client_cls):
    mock_async_client_cls.return_value = _mock_httpx_context([])

    response = client.post(
        "/generate",
        json={"topic": "income_protection"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "income_protection"
    assert "Not enough data" in data["headline"]


# --- spending_analysis ---

@patch("app.main.httpx.AsyncClient")
def test_spending_analysis_with_data(mock_async_client_cls):
    today = datetime.date.today()
    transactions = []
    for i in range(1, 5):
        d = today - datetime.timedelta(days=30 * i)
        transactions.append({"date": d.isoformat(), "amount": -500.0, "description": "Groceries"})
    transactions.append({"date": today.isoformat(), "amount": -800.0, "description": "Groceries"})

    mock_async_client_cls.return_value = _mock_httpx_context(transactions)

    response = client.post(
        "/generate",
        json={"topic": "spending_analysis"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "spending_analysis"


@patch("app.main.httpx.AsyncClient")
def test_spending_analysis_insufficient_data(mock_async_client_cls):
    today = datetime.date.today()
    transactions = [{"date": today.isoformat(), "amount": -100.0, "description": "Coffee"}]
    mock_async_client_cls.return_value = _mock_httpx_context(transactions)

    response = client.post(
        "/generate",
        json={"topic": "spending_analysis"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Not enough data" in data["headline"] or "first month" in data["headline"].lower()


# --- savings_potential ---

@patch("app.main.httpx.AsyncClient")
def test_savings_potential_with_subscriptions(mock_async_client_cls):
    today = datetime.date.today()
    transactions = [
        {"date": (today - datetime.timedelta(days=10)).isoformat(), "amount": -9.99, "description": "Netflix Monthly"},
        {"date": (today - datetime.timedelta(days=10)).isoformat(), "amount": -14.99, "description": "Spotify Premium"},
    ]
    mock_async_client_cls.return_value = _mock_httpx_context(transactions)

    response = client.post(
        "/generate",
        json={"topic": "savings_potential"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "savings_potential"
    assert "save" in data["headline"].lower() or "£" in data["headline"]


@patch("app.main.httpx.AsyncClient")
def test_savings_potential_no_subscriptions(mock_async_client_cls):
    today = datetime.date.today()
    transactions = [
        {"date": (today - datetime.timedelta(days=5)).isoformat(), "amount": -50.0, "description": "Groceries at Tesco store"},
    ]
    mock_async_client_cls.return_value = _mock_httpx_context(transactions)

    response = client.post(
        "/generate",
        json={"topic": "savings_potential"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "savings_potential"
    assert "No recurring subscriptions" in data["headline"]


# --- Upstream failure ---

@patch("app.main.httpx.AsyncClient")
def test_generate_returns_502_on_upstream_failure(mock_async_client_cls):
    import httpx as _httpx

    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = _httpx.RequestError("connection refused")
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    mock_async_client_cls.return_value = mock_client_instance

    response = client.post(
        "/generate",
        json={"topic": "income_protection"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 502
