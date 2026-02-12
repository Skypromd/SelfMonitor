import os
import tempfile
from pathlib import Path

import httpx
import pytest
from pact import Pact
from pact.match import like

if os.getenv("ENABLE_CONTRACT_TESTS") != "1":
    pytest.skip(
        "Contract tests are disabled. Set ENABLE_CONTRACT_TESTS=1 to run.",
        allow_module_level=True,
    )

CONSUMER_NAME = "TaxEngineService"
PROVIDER_NAME = "TransactionsService"
PACT_OUTPUT_DIR = Path(os.getenv("PACT_OUTPUT_DIR", Path(tempfile.gettempdir()) / "pacts"))
PACT_FILE = PACT_OUTPUT_DIR / f"{CONSUMER_NAME}-{PROVIDER_NAME}.json"


def test_get_all_transactions_for_a_user():
    pact = Pact(CONSUMER_NAME, PROVIDER_NAME)

    (
        pact.upon_receiving("a request for all of a user's transactions")
        .given("transactions exist for a user")
        .with_request("GET", "/transactions/me")
        .with_header("Authorization", "Bearer fake-token", "Request")
        .will_respond_with(200)
        .with_header("Content-Type", "application/json", "Response")
        .with_body(
            [
                {
                    "id": like("123e4567-e89b-12d3-a456-426614174000"),
                    "account_id": like("123e4567-e89b-12d3-a456-426614174001"),
                    "user_id": "test_user",
                    "provider_transaction_id": like("txn_abc"),
                    "date": like("2023-10-10"),
                    "description": like("Tesco"),
                    "amount": like(123.45),
                    "currency": like("GBP"),
                    "category": like("groceries"),
                    "created_at": like("2023-10-10T10:00:00Z"),
                }
            ],
            part="Response",
        )
    )

    with pact.serve() as mock_server:
        response = httpx.get(
            f"{mock_server.url}/transactions/me",
            headers={"Authorization": "Bearer fake-token"},
            timeout=5.0,
        )
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert payload

        mock_server.write_file(PACT_OUTPUT_DIR, overwrite=True)

    assert PACT_FILE.exists()

