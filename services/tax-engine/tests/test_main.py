import pytest
from fastapi.testclient import TestClient
import httpx
from jose import jwt

# Adjust path to import app
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app

client = TestClient(app)
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_calculate_tax_with_mocked_transactions(mocker):
    """
    Tests the tax calculation logic by providing a mocked response
    from the transactions-service.
    """
    # 1. Prepare mock data that transactions-service would return
    mock_transactions = [
        {"date": "2023-05-10", "amount": 3000.0, "category": "income"},
        {"date": "2023-06-15", "amount": -150.0, "category": "transport"}, # Deductible
        {"date": "2023-07-20", "amount": -80.0, "category": "groceries"},   # Not deductible
        {"date": "2023-08-01", "amount": -50.0, "category": "office_supplies"}, # Deductible
    ]

    # 2. Mock the httpx.AsyncClient.get call
    mock_response = httpx.Response(200, json=mock_transactions)
    mock_get = mocker.patch(
        "httpx.AsyncClient.get",
        return_value=mock_response
    )

    # 3. Call the /calculate endpoint
    response = client.post(
        "/calculate",
        headers=get_auth_headers(),
        json={"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"}
    )

    # 4. Assert the results
    assert response.status_code == 200
    data = response.json()

    # Check that the mock was called
    mock_get.assert_called_once()

    # Check the calculation logic
    # Total income = 3000
    # Total deductible expenses = 150 (transport) + 50 (office_supplies) = 200
    # Taxable profit = 3000 - 200 = 2800
    # Personal allowance = 12570. Since 2800 < 12570, taxable amount is 0.
    # Estimated tax = 0
    assert data["total_income"] == 3000.0
    assert data["total_expenses"] == 200.0
    assert data["estimated_tax_due"] == 0.0

@pytest.mark.asyncio
async def test_calculate_tax_service_unavailable(mocker):
    """
    Tests that the endpoint handles the case where transactions-service is down.
    """
    # Mock the httpx call to raise an error
    mocker.patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("Connection refused")
    )

    response = client.post(
        "/calculate",
        headers=get_auth_headers(),
        json={"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"}
    )

    assert response.status_code == 502 # Bad Gateway
    assert "Could not connect to transactions-service" in response.json()["detail"]
