import os
import sys
from collections import deque

import httpx
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


def test_submit_hmrc_mtd_quarterly_update_accepts_valid_payload(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
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
    assert payload["transmission_mode"] == "simulated"


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


def test_submit_hmrc_mtd_quarterly_update_direct_mode(monkeypatch):
    async def _fake_fetch_token(**_kwargs):
        return "fake-access-token"

    async def _fake_post_quarterly(**_kwargs):
        return httpx.Response(
            202,
            json={"submissionId": "hmrc-direct-submission-id"},
            request=httpx.Request("POST", "https://test-api.service.hmrc.gov.uk/itsa/quarterly-updates"),
        )

    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr("app.hmrc_mtd._fetch_hmrc_oauth_access_token", _fake_fetch_token)
    monkeypatch.setattr("app.hmrc_mtd._post_hmrc_quarterly_update", _fake_post_quarterly)

    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=_valid_quarterly_payload(),
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["transmission_mode"] == "direct"
    assert payload["hmrc_status_code"] == 202
    assert payload["hmrc_receipt_reference"] == "hmrc-direct-submission-id"


def test_submit_hmrc_mtd_quarterly_update_direct_mode_requires_credentials(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "")

    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=_valid_quarterly_payload(),
    )

    assert response.status_code == 400
    assert "OAuth credentials are missing" in response.json()["detail"]


def test_submit_hmrc_mtd_quarterly_update_uses_fallback_when_enabled(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_FALLBACK_TO_SIMULATION", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "")
    monkeypatch.setattr("app.main.HMRC_SUBMISSION_EVENTS", deque(maxlen=200))

    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=_valid_quarterly_payload(),
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["transmission_mode"] == "simulated"
    assert "Fallback applied" in payload["message"]


def test_hmrc_mtd_submission_slo_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.main.HMRC_SUBMISSION_EVENTS",
        deque(
            [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "success": True,
                    "latency_ms": 900.0,
                    "transmission_mode": "direct",
                    "used_fallback": False,
                },
                {
                    "timestamp": "2026-01-02T00:00:00Z",
                    "success": False,
                    "latency_ms": 3000.0,
                    "transmission_mode": "simulated",
                    "used_fallback": True,
                },
            ],
            maxlen=200,
        ),
    )
    monkeypatch.setattr("app.main.HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT", 99.0)
    monkeypatch.setattr("app.main.HMRC_SLO_P95_LATENCY_TARGET_MS", 2500.0)

    response = client.get("/integrations/hmrc/mtd/submission-slo", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_submissions"] == 2
    assert payload["successful_submissions"] == 1
    assert payload["failed_submissions"] == 1
    assert payload["fallback_submissions"] == 1
    assert payload["direct_mode_submissions"] == 1
    assert payload["simulated_mode_submissions"] == 1
    assert payload["success_rate_percent"] == 50.0
    assert payload["success_rate_alert"] is True
    assert payload["latency_alert"] is True


def test_hmrc_mtd_operational_readiness_endpoint(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_FALLBACK_TO_SIMULATION", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr("app.main.HMRC_OAUTH_TOKEN_URL", "https://example.test/oauth/token")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CREDENTIALS_ROTATED_AT", "2026-01-10")
    monkeypatch.setattr("app.main.HMRC_OAUTH_ROTATION_MAX_AGE_DAYS", 120)

    response = client.get("/integrations/hmrc/mtd/operational-readiness", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["direct_submission_enabled"] is True
    assert payload["fallback_to_simulation_enabled"] is True
    assert payload["oauth_credentials_configured"] is True
    assert payload["readiness_band"] in {"ready", "degraded", "not_ready"}
