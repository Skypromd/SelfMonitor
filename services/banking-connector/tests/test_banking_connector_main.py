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
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

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

@pytest.mark.asyncio
async def test_callback_schedules_celery_task(mocker):
    """
    Test that the callback endpoint correctly dispatches a Celery task.
    """
    # Mock the .delay() method of our Celery task
    mock_delay = mocker.patch.object(import_transactions_task, 'delay')
    mock_delay.return_value.id = "task-123"

    # Use a dummy code to trigger the endpoint
    auth_code = "test-auth-code"
    response = client.get(f"/connections/callback?code={auth_code}", headers=get_auth_headers())

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'processing'
    assert 'task_id' in data
    assert data['task_id'] == "task-123"

    # Check that our mock was called
    mock_delay.assert_called_once()

    # Verify the contents of the call
    call_args = mock_delay.call_args.args
    account_id_str = call_args[0]
    task_user_id = call_args[1]
    task_token = call_args[2]
    transactions_data = call_args[3]

    # Check that a valid UUID string is passed
    assert isinstance(uuid.UUID(account_id_str), uuid.UUID)

    assert task_user_id == TEST_USER_ID
    assert isinstance(task_token, str)
    assert len(task_token) > 10

    assert isinstance(transactions_data, list)
    assert len(transactions_data) == 2
    assert transactions_data[0]['description'] == "Tesco"
    assert auth_token
