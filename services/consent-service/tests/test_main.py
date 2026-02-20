import pytest
import uuid
from fastapi.testclient import TestClient
from jose import jwt
# We need to adjust the path to import the app from the parent directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app, Consent, insert_consent_for_tests, reset_consent_db_for_tests

client = TestClient(app)
TEST_AUTH_SECRET = "a_very_secret_key_that_should_be_in_an_env_var"
TEST_AUTH_ALGORITHM = "HS256"


def auth_headers(user_id: str = "fake-user-123") -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def setup_and_teardown():
    reset_consent_db_for_tests()
    yield

def test_record_consent_triggers_audit(mocker):
    """
    Test that creating a consent successfully calls the audit log function.
    """
    # Mock the async function that calls the compliance service
    mock_log_audit = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock)

    connection_id = str(uuid.uuid4())
    response = client.post(
        "/consents",
        headers=auth_headers(),
        json={
            "connection_id": connection_id,
            "provider": "test_bank",
            "scopes": ["accounts", "transactions"]
        }
    )

    assert response.status_code == 201

    # Check that our mock was called correctly
    mock_log_audit.assert_awaited_once()
    call_args = mock_log_audit.call_args.kwargs
    assert call_args['action'] == "consent.granted"
    assert call_args['details']['provider'] == "test_bank"
    assert 'consent_id' in call_args['details']

def test_revoke_consent_triggers_audit(mocker):
    """
    Test that revoking a consent successfully calls the audit log function.
    """
    # 1. First, create a consent directly in persistent storage
    consent_id = uuid.uuid4()
    user_id = "fake-user-123"
    insert_consent_for_tests(Consent(
        id=consent_id,
        user_id=user_id,
        connection_id=uuid.uuid4(),
        provider="test_bank",
        scopes=["transactions"]
    ))

    # 2. Mock the audit log function
    mock_log_audit = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock)

    # 3. Call the endpoint to revoke the consent
    response = client.delete(f"/consents/{consent_id}", headers=auth_headers(user_id))

    assert response.status_code == 204

    # 4. Check that our mock was called correctly
    mock_log_audit.assert_awaited_once()
    call_args = mock_log_audit.call_args.kwargs
    assert call_args['user_id'] == user_id
    assert call_args['action'] == "consent.revoked"
    assert call_args['details']['consent_id'] == str(consent_id)
