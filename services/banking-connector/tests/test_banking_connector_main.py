import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Adjust path to import app and other modules
import sys
import os

os.environ["AUTH_SECRET_KEY"] = "test-secret"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# conftest.py sets BANKING_CONNECTIONS_STORE_PATH before this import
from app.main import app, import_transactions_task

client = TestClient(app)
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": user_id,
            "plan": "starter",
            "bank_connections_limit": 10,
            "bank_sync_daily_limit": 3,
            "transactions_per_month_limit": 500,
            "storage_limit_gb": 2,
        },
        AUTH_SECRET_KEY,
        algorithm=AUTH_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}

def test_sync_quota_returns_limits():
    response = client.get("/connections/sync-quota", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data.get("daily_limit") == 3
    assert "used_today" in data and "remaining" in data


def test_list_providers_public():
    response = client.get("/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = {p["id"] for p in data}
    assert "mock_bank" in ids
    assert data[0]["id"] == "saltedge"
    for p in data:
        assert set(p.keys()) == {"id", "display_name", "configured", "logo_url"}
        assert p["configured"] in ("true", "false")
        assert p["logo_url"].startswith("https://")


def test_initiate_connection_success():
    """
    Test that the /connections/initiate endpoint returns a well-formed consent URL.
    """
    response = client.post(
        "/connections/initiate",
        headers=get_auth_headers(),
        json={"provider_id": "mock_bank", "redirect_uri": "https://my-app.com/callback"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "consent_url" in data
    assert "https://fake-bank-provider.com/consent" in data["consent_url"]
    assert "client_id=mock_bank" in data["consent_url"]


def test_initiate_truelayer_returns_truelayer_auth_url():
    response = client.post(
        "/connections/initiate",
        headers=get_auth_headers(),
        json={"provider_id": "truelayer", "redirect_uri": "http://localhost:3000/callback"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "truelayer" in data["consent_url"].lower()
    assert "response_type=code" in data["consent_url"]
    assert data["provider"].startswith("truelayer")

def test_callback_schedules_celery_task():
    """
    Test that the callback endpoint correctly dispatches a Celery task.
    """
    if import_transactions_task is None:
        pytest.skip("Celery import_transactions_task not available in this environment")

    with patch.object(import_transactions_task, "delay") as mock_delay:
        mock_delay.return_value = MagicMock(id="task-123")

        auth_code = "test-auth-code"
        response = client.get(
            f"/connections/callback?code={auth_code}&provider_id=mock_bank",
            headers=get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "task_id" in data
        assert data["task_id"] == "task-123"

        mock_delay.assert_called_once()

        call_args = mock_delay.call_args.args
        account_id_str = call_args[0]
        task_user_id = call_args[1]
        task_token = call_args[2]
        transactions_data = call_args[3]

        assert isinstance(uuid.UUID(account_id_str), uuid.UUID)

        assert task_user_id == TEST_USER_ID
        assert isinstance(task_token, str)
        assert len(task_token) > 10

        assert isinstance(transactions_data, list)
        assert len(transactions_data) == 2
        assert transactions_data[0]["description"] == "Tesco"
        assert isinstance(task_token, str) and len(task_token) > 0


def test_exports_statement_csv_filters_and_escapes():
    today = datetime.date.today()
    tid = str(uuid.uuid4())
    aid = str(uuid.uuid4())
    txs = [
        {
            "id": tid,
            "account_id": aid,
            "user_id": TEST_USER_ID,
            "provider_transaction_id": "p1",
            "date": today.isoformat(),
            "description": 'Pay "Client", Ltd',
            "amount": -10.5,
            "currency": "GBP",
            "category": "food",
            "tax_category": None,
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": str(uuid.uuid4()),
            "account_id": aid,
            "user_id": TEST_USER_ID,
            "provider_transaction_id": "p-old",
            "date": (today - datetime.timedelta(days=400)).isoformat(),
            "description": "old",
            "amount": 1.0,
            "currency": "GBP",
            "category": None,
            "tax_category": None,
            "created_at": "2026-01-01T00:00:00Z",
        },
    ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = txs
    mock_resp.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_resp)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.main.httpx.AsyncClient", return_value=mock_cm):
        response = client.get("/exports/statement-csv?days=200", headers=get_auth_headers())

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    text = response.text
    assert tid in text
    assert "p-old" not in text
    assert '""Client""' in text
    called_url = mock_client_instance.get.await_args[0][0]
    assert called_url.endswith("/transactions/me")


def test_exports_statement_csv_upstream_error():
    resp401 = MagicMock()
    resp401.status_code = 401
    resp401.json = MagicMock(return_value={"detail": "nope"})
    err = httpx.HTTPStatusError("x", request=MagicMock(), response=resp401)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(side_effect=err)

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_resp)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.main.httpx.AsyncClient", return_value=mock_cm):
        response = client.get("/exports/statement-csv", headers=get_auth_headers())

    assert response.status_code == 401
    assert response.json()["detail"] == "nope"
