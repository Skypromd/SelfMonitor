import httpx
import uuid
import time
import os

# URL'ы наших сервисов, как они доступны снаружи Docker через API Gateway
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000/api")

def register_and_login():
    unique_email = f"testuser_{uuid.uuid4()}@example.com"
    password = "a_strong_password"

    reg_response = httpx.post(
        f"{API_GATEWAY_URL}/auth/register",
        json={"email": unique_email, "password": password}
    )
    assert reg_response.status_code == 201

    login_response = httpx.post(
        f"{API_GATEWAY_URL}/auth/token",
        data={"username": unique_email, "password": password}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_user_registration_and_profile_creation():
    """
    This is an integration test that checks the flow between
    auth-service and user-profile-service via the API Gateway.
    It assumes the services are running (via docker-compose).
    """
    unique_email = f"testuser_{uuid.uuid4()}@example.com"
    password = "a_strong_password"

    # 1. Register a new user in auth-service
    reg_response = httpx.post(
        f"{API_GATEWAY_URL}/auth/register",
        json={"email": unique_email, "password": password}
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
    # 1. Create a user and get a valid JWT for downstream service auth
    auth_headers = register_and_login()

    # 2. Trigger the flow by calling the banking-connector callback
    callback_response = httpx.get(
        f"{API_GATEWAY_URL}/banking/connections/callback?code=integration-test-code",
        headers=auth_headers
    )
    assert callback_response.status_code == 200
    callback_data = callback_response.json()
    account_id = callback_data["connection_id"]
    print(f"Callback successful. Account ID: {account_id}. Celery task ID: {callback_data['task_id']}")

    # 3. Wait for the asynchronous processing to complete.
    # In a real-world test suite, we might use more sophisticated polling
    # or check the Celery task status, but sleep is simple and effective here.
    print("Waiting for Celery worker to process the task...")
    time.sleep(8) # Give enough time for Celery task (mocked 2s) + network calls

    # 4. Verify the final result in the transactions-service
    get_trans_response = httpx.get(
        f"{API_GATEWAY_URL}/transactions/accounts/{account_id}/transactions",
        headers=auth_headers
    )

    assert get_trans_response.status_code == 200
    transactions = get_trans_response.json()

    print("Received transactions from transactions-service:", transactions)

    # 5. Assert that the data is correct and auto-categorization worked
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
