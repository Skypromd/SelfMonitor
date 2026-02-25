import uuid
import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Adjust path to import app and other modules
import sys
import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app, import_transactions_task

client = TestClient(app)
TEST_AUTH_SECRET = "test-secret"
TEST_AUTH_ALGORITHM = "HS256"


def auth_headers(user_id: str = "fake-user-123") -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

def test_initiate_connection_success():
    """
    Test that the /connections/initiate endpoint returns a well-formed consent URL.
    """
    response = client.post(
        "/connections/initiate",
        headers=auth_headers(),
        json={"provider_id": "mock_bank", "redirect_uri": "https://my-app.com/callback"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "consent_url" in data
    assert "https://fake-bank-provider.com/consent" in data["consent_url"]
    assert "client_id=mock_bank" in data["consent_url"]

@pytest.mark.asyncio
async def test_callback_schedules_celery_task(mocker):
    """
    Test that the callback endpoint correctly dispatches a Celery task.
    """
    # Mock the .delay() method of our Celery task
    mock_delay = mocker.patch.object(import_transactions_task, 'delay')
    mock_delay.return_value.id = "test-task-id"
    headers = auth_headers()

    # Use a dummy code to trigger the endpoint
    auth_code = "test-auth-code"
    response = client.get(f"/connections/callback?code={auth_code}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'processing'
    assert 'task_id' in data

    # Check that our mock was called
    mock_delay.assert_called_once()

    # Verify the contents of the call
    call_args = mock_delay.call_args.args
    account_id_str = call_args[0]
    transactions_data = call_args[1]
    auth_token = call_args[2]

    # Check that a valid UUID string is passed
    assert isinstance(uuid.UUID(account_id_str), uuid.UUID)

    assert isinstance(transactions_data, list)
    assert len(transactions_data) == 2
    assert transactions_data[0]['description'] == "Tesco"
    assert auth_token
