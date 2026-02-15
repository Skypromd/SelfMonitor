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
    mock_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
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
    assert data["taxable_profit"] == 2800.0
    assert data["personal_allowance_used"] == 2800.0
    assert data["estimated_income_tax_due"] == 0.0
    assert data["estimated_class4_nic_due"] == 0.0
    assert data["estimated_tax_due"] == 0.0
    assert data["mtd_obligation"]["reporting_required"] is False
    assert data["mtd_obligation"]["reporting_cadence"] == "annual_only"


@pytest.mark.asyncio
async def test_calculate_tax_includes_class4_nic_for_higher_profit(mocker):
    mock_transactions = [
        {"date": "2023-05-10", "amount": 70000.0, "category": "income"},
        {"date": "2023-06-15", "amount": -2000.0, "category": "transport"},
    ]
    mock_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

    response = client.post(
        "/calculate",
        headers=get_auth_headers(),
        json={"start_date": "2023-01-01", "end_date": "2023-12-31", "jurisdiction": "UK"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["taxable_profit"] == 68000.0
    assert payload["estimated_income_tax_due"] > 0
    assert payload["estimated_class4_nic_due"] > 0
    assert payload["estimated_tax_due"] == round(
        payload["estimated_income_tax_due"] + payload["estimated_class4_nic_due"],
        2,
    )
    assert payload["mtd_obligation"]["reporting_required"] is False


@pytest.mark.asyncio
async def test_calculate_tax_flags_quarterly_reporting_when_income_exceeds_50000(mocker):
    mock_transactions = [
        {"date": "2026-05-10", "amount": 60000.0, "category": "income"},
        {"date": "2026-06-20", "amount": -5000.0, "category": "transport"},
    ]
    mock_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

    response = client.post(
        "/calculate",
        headers=get_auth_headers(),
        json={"start_date": "2026-04-06", "end_date": "2027-04-05", "jurisdiction": "UK"},
    )
    assert response.status_code == 200
    payload = response.json()
    mtd = payload["mtd_obligation"]
    assert mtd["policy_code"] == "UK_MTD_ITSA_2026"
    assert mtd["threshold"] == 50000.0
    assert mtd["reporting_required"] is True
    assert mtd["reporting_cadence"] == "quarterly_updates_plus_final_declaration"
    assert len(mtd["quarterly_updates"]) == 4
    assert mtd["quarterly_updates"][0]["quarter"] == "Q1"

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


@pytest.mark.asyncio
async def test_calculate_and_submit_returns_mtd_obligation_and_creates_quarterly_reminders(mocker):
    mock_transactions = [
        {"date": "2026-05-10", "amount": 60000.0, "category": "income"},
        {"date": "2026-06-15", "amount": -3000.0, "category": "transport"},
    ]
    mock_get_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    mocker.patch("httpx.AsyncClient.get", return_value=mock_get_response)

    mock_post = mocker.patch(
        "app.main.post_json_with_retry",
        side_effect=[
            {"submission_id": "mock-submission-id"},
            None,
            None,
            None,
            None,
            None,
        ],
    )

    response = client.post(
        "/calculate-and-submit",
        headers=get_auth_headers(),
        json={"start_date": "2026-04-06", "end_date": "2027-04-05", "jurisdiction": "UK"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["submission_id"] == "mock-submission-id"
    assert payload["submission_mode"] == "annual_tax_return"
    assert payload["mtd_obligation"]["reporting_required"] is True
    assert len(payload["mtd_obligation"]["quarterly_updates"]) == 4
    assert mock_post.call_count == 6


@pytest.mark.asyncio
async def test_calculate_and_submit_uses_mtd_quarterly_endpoint_for_quarter_window(mocker):
    mock_transactions = [
        {"date": "2026-04-10", "amount": 20000.0, "category": "income"},
        {"date": "2026-05-15", "amount": -1000.0, "category": "transport"},
    ]
    mock_get_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    mocker.patch("httpx.AsyncClient.get", return_value=mock_get_response)

    mock_post = mocker.patch(
        "app.main.post_json_with_retry",
        side_effect=[
            {"submission_id": "quarterly-submission-id"},
            None,
            None,
            None,
            None,
            None,
        ],
    )

    response = client.post(
        "/calculate-and-submit",
        headers=get_auth_headers(),
        json={"start_date": "2026-04-06", "end_date": "2026-07-05", "jurisdiction": "UK"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["submission_mode"] == "mtd_quarterly_update"
    first_call = mock_post.call_args_list[0]
    assert first_call.args[0].endswith("/integrations/hmrc/mtd/quarterly-update")
    submitted_payload = first_call.kwargs["json_body"]
    assert submitted_payload["report"]["period"]["quarter"] == "Q1"
    assert submitted_payload["report"]["schema_version"] == "hmrc-mtd-itsa-quarterly-v1"


@pytest.mark.asyncio
async def test_calculate_and_submit_rejects_non_quarter_partial_period_when_mtd_required(mocker):
    mock_transactions = [
        {"date": "2026-05-10", "amount": 25000.0, "category": "income"},
        {"date": "2026-06-15", "amount": -1200.0, "category": "transport"},
    ]
    mock_get_response = httpx.Response(
        200,
        json=mock_transactions,
        request=httpx.Request("GET", "http://transactions-service/transactions/me"),
    )
    mocker.patch("httpx.AsyncClient.get", return_value=mock_get_response)

    response = client.post(
        "/calculate-and-submit",
        headers=get_auth_headers(),
        json={"start_date": "2026-04-06", "end_date": "2026-08-01", "jurisdiction": "UK"},
    )

    assert response.status_code == 400
    assert "submission period must match an HMRC quarter" in response.json()["detail"]
