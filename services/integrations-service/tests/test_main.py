import os
import sys

from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app


client = TestClient(app)
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "integration-user@example.com"


def _headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _valid_quarterly_payload() -> dict[str, object]:
    return {
        "submission_channel": "api",
        "correlation_id": "corr-123",
        "report": {
            "schema_version": "hmrc-mtd-itsa-quarterly-v1",
            "jurisdiction": "UK",
            "policy_code": "UK_MTD_ITSA_2026",
            "generated_at": "2026-07-10T10:00:00Z",
            "business": {
                "taxpayer_ref": "UTR-1234567890",
                "business_name": "Acme Sole Trader",
                "accounting_method": "cash",
            },
            "period": {
                "tax_year_start": "2026-04-06",
                "tax_year_end": "2027-04-05",
                "quarter": "Q1",
                "period_start": "2026-04-06",
                "period_end": "2026-07-05",
                "due_date": "2026-08-05",
            },
            "financials": {
                "turnover": 25000.0,
                "allowable_expenses": 5000.0,
                "taxable_profit": 20000.0,
                "estimated_tax_due": 3200.0,
                "currency": "GBP",
            },
            "category_summary": [
                {"category": "income", "total_amount": 25000.0, "taxable_amount": 25000.0},
                {"category": "transport", "total_amount": -5000.0, "taxable_amount": -5000.0},
            ],
            "declaration": "true_and_complete",
        },
    }


def test_hmrc_mtd_spec_endpoint():
    response = client.get(
        "/integrations/hmrc/mtd/quarterly-update/spec",
        headers=_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "hmrc-mtd-itsa-quarterly-v1"
    assert "report.period" in payload["required_sections"]


def test_submit_hmrc_mtd_quarterly_update_accepts_valid_payload():
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=_valid_quarterly_payload(),
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["submission_type"] == "mtd_quarterly_update"
    assert payload["hmrc_receipt_reference"].startswith("HMRC-MTD-")
    assert payload["hmrc_endpoint"].endswith("/itsa/quarterly-updates")


def test_submit_hmrc_mtd_quarterly_update_rejects_invalid_period_alignment():
    invalid_payload = _valid_quarterly_payload()
    invalid_payload["report"]["period"]["period_end"] = "2026-07-04"

    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=invalid_payload,
    )
    assert response.status_code == 400
    assert "Invalid HMRC MTD quarterly report format" in response.json()["detail"]
