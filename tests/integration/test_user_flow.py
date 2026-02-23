import httpx
import uuid
import time
import os
import pytest

# URL'ы наших сервисов, как они доступны снаружи Docker через API Gateway
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000/api")

def _ensure_integration_ready():
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to run.")
    try:
        httpx.get(API_GATEWAY_URL, timeout=2.0)
    except Exception:
        pytest.skip("API Gateway not reachable.")

def test_user_registration_and_profile_creation():
    """
    This is an integration test that checks the flow between
    auth-service and user-profile-service via the API Gateway.
    It assumes the services are running (via docker-compose).
    """
    unique_email = f"testuser_{uuid.uuid4()}@example.com"
    password = "a_strong_password"

    # 1. Register a new user in auth-service
    _ensure_integration_ready()
    reg_response = httpx.post(
        f"{API_GATEWAY_URL}/auth/register",
        data={"username": unique_email, "password": password}
    )
    assert reg_response.status_code == 201
    print(f"User {unique_email} registered successfully.")

    # 2. Log in to get a JWT token
    login_response = httpx.post(
        f"{API_GATEWAY_URL}/auth/token",
        data={"username": unique_email, "password": password}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    print("Login successful, token received.")

    # 3. Use the token to create a profile in user-profile-service
    profile_data = {
        "first_name": "Integration",
        "last_name": "Test",
        "date_of_birth": "1999-12-31"
    }
    create_profile_response = httpx.put(
        f"{API_GATEWAY_URL}/profile/profiles/me",
        headers=auth_headers,
        json=profile_data
    )
    assert create_profile_response.status_code == 200
    print("Profile created successfully.")

    # 4. Use the token again to verify that the profile was saved
    get_profile_response = httpx.get(
        f"{API_GATEWAY_URL}/profile/profiles/me",
        headers=auth_headers
    )
    assert get_profile_response.status_code == 200
    profile = get_profile_response.json()
    assert profile["first_name"] == "Integration"
    assert profile["last_name"] == "Test"
    print("Profile data verified successfully. Integration test passed!")


def test_full_transaction_import_flow():
    """
    Tests the full asynchronous flow:
    1. banking-connector receives a callback.
    2. It dispatches a Celery task.
    3. The celery-worker picks up the task.
    4. The worker calls transactions-service, which calls categorization-service.
    5. The final, categorized data is written to the database.
    """
    # 1. Trigger the flow by calling the banking-connector callback
    _ensure_integration_ready()
    callback_response = httpx.get(
        f"{API_GATEWAY_URL}/banking/connections/callback?code=integration-test-code"
    )
    assert callback_response.status_code == 200
    callback_data = callback_response.json()
    account_id = callback_data["account_id"]
    print(f"Callback successful. Account ID: {account_id}. Celery task ID: {callback_data['task_id']}")

    # 2. Wait for the asynchronous processing to complete.
    # In a real-world test suite, we might use more sophisticated polling
    # or check the Celery task status, but sleep is simple and effective here.
    print("Waiting for Celery worker to process the task...")
    time.sleep(8) # Give enough time for Celery task (mocked 2s) + network calls

    # 3. Verify the final result in the transactions-service
    # We need auth for this, but our fake_auth_check uses a static user_id,
    # so we don't need a real token for this specific test.
    get_trans_response = httpx.get(
        f"{API_GATEWAY_URL}/transactions/accounts/{account_id}/transactions",
        headers={"Authorization": "Bearer fake-token"} # This is for passing the auth check
    )

    assert get_trans_response.status_code == 200
    transactions = get_trans_response.json()

    print("Received transactions from transactions-service:", transactions)

    # 4. Assert that the data is correct and auto-categorization worked
    assert len(transactions) == 2

    tesco_transaction = next((t for t in transactions if t['description'] == 'Tesco'), None)
    amazon_transaction = next((t for t in transactions if t['description'] == 'Amazon'), None)

    assert tesco_transaction is not None
    assert amazon_transaction is not None

    # This is the most important assertion: check if auto-categorization was successful
    assert tesco_transaction['category'] == 'groceries'
    # And check that a transaction without a rule was not categorized
    assert amazon_transaction['category'] is None

    print("Integration test for transaction import and categorization passed!")
