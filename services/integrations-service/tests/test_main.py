import os
import sys
from collections import deque

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret")

import httpx
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "integration-user@example.com"


def _headers(
    user_id: str = TEST_USER_ID,
    *,
    plan: str | None = None,
    hmrc_direct_submission: bool | None = None,
) -> dict[str, str]:
    claims: dict[str, object] = {"sub": user_id}
    if plan is not None:
        claims["plan"] = plan
    if hmrc_direct_submission is not None:
        claims["hmrc_direct_submission"] = hmrc_direct_submission
    token = jwt.encode(claims, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _web_fraud_client_context() -> dict[str, object]:
    return {
        "client_type": "web",
        "user_agent": "Mozilla/5.0 (compatible; pytest-integration)",
        "session_id": "pytest-web-session",
    }


def _mobile_fraud_client_context() -> dict[str, object]:
    return {
        "client_type": "mobile",
        "user_agent": "MyNetTaxMobile/1.0.0 (pytest)",
        "device_id": "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee",
    }


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


def test_resolve_hmrc_urls_sandbox(monkeypatch):
    monkeypatch.setenv("HMRC_ENV", "sandbox")
    monkeypatch.delenv("HMRC_DIRECT_API_BASE_URL", raising=False)
    monkeypatch.delenv("HMRC_OAUTH_TOKEN_URL", raising=False)
    from app.main import resolve_hmrc_urls_from_env

    api, token, label = resolve_hmrc_urls_from_env()
    assert label == "sandbox"
    assert "test-api.service.hmrc.gov.uk" in api
    assert "oauth/token" in token


def test_resolve_hmrc_urls_production(monkeypatch):
    monkeypatch.setenv("HMRC_ENV", "production")
    monkeypatch.delenv("HMRC_DIRECT_API_BASE_URL", raising=False)
    monkeypatch.delenv("HMRC_OAUTH_TOKEN_URL", raising=False)
    from app.main import resolve_hmrc_urls_from_env

    api, token, label = resolve_hmrc_urls_from_env()
    assert label == "production"
    assert api.startswith("https://api.service.hmrc.gov.uk")


def test_hmrc_mtd_spec_endpoint():
    response = client.get(
        "/integrations/hmrc/mtd/quarterly-update/spec",
        headers=_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "hmrc-mtd-itsa-quarterly-v1"
    assert "report.period" in payload["required_sections"]


def _isolated_db(monkeypatch, tmp_path):
    db = tmp_path / "integrations-isolated.db"
    monkeypatch.setattr("app.main.INTEGRATIONS_DB_PATH", str(db))
    from app.main import init_integrations_db

    init_integrations_db()


def test_submit_hmrc_mtd_quarterly_update_rejects_without_confirmation_when_required(
    monkeypatch, tmp_path
):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_REQUIRE_EXPLICIT_CONFIRM", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=_valid_quarterly_payload(),
    )
    assert response.status_code == 403
    assert "explicit confirmation" in response.json()["detail"].lower()


def test_internal_mtd_quarterly_draft_forbidden(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setenv("INTERNAL_SERVICE_SECRET", "sec-internal-draft-1")
    report = _valid_quarterly_payload()["report"]
    r = client.post(
        "/internal/hmrc/mtd/quarterly-update/draft",
        json={"user_id": TEST_USER_ID, "report": report},
        headers={"X-Internal-Token": "wrong-token"},
    )
    assert r.status_code == 403


def test_internal_mtd_quarterly_draft_ok(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setenv("INTERNAL_SERVICE_SECRET", "sec-internal-draft-1")
    report = _valid_quarterly_payload()["report"]
    r = client.post(
        "/internal/hmrc/mtd/quarterly-update/draft",
        json={"user_id": "internal-draft-user@example.com", "report": report},
        headers={"X-Internal-Token": "sec-internal-draft-1"},
    )
    assert r.status_code == 201
    assert r.json().get("draft_id")


def test_mtd_draft_latest_empty(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    r = client.get("/integrations/hmrc/mtd/quarterly-update/draft/latest", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert body.get("draft_id") is None


def test_mtd_confirm_blocked_while_awaiting_accountant(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_REQUIRE_EXPLICIT_CONFIRM", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    report = _valid_quarterly_payload()["report"]
    r_draft = client.post(
        "/integrations/hmrc/mtd/quarterly-update/draft",
        headers=_headers(),
        json={"report": report},
    )
    assert r_draft.status_code == 201
    draft_id = r_draft.json()["draft_id"]
    r_tr = client.post(
        f"/integrations/hmrc/mtd/quarterly-update/draft/{draft_id}/workflow",
        headers=_headers(),
        json={"target_status": "ready_for_accountant_review"},
    )
    assert r_tr.status_code == 200
    r_conf = client.post(
        "/integrations/hmrc/mtd/quarterly-update/confirm",
        headers=_headers(),
        json={"draft_id": draft_id},
    )
    assert r_conf.status_code == 409


def test_hmrc_mtd_draft_confirm_submit_flow(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_REQUIRE_EXPLICIT_CONFIRM", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    report = _valid_quarterly_payload()["report"]
    r_draft = client.post(
        "/integrations/hmrc/mtd/quarterly-update/draft",
        headers=_headers(),
        json={"report": report},
    )
    assert r_draft.status_code == 201
    draft_id = r_draft.json()["draft_id"]
    r_conf = client.post(
        "/integrations/hmrc/mtd/quarterly-update/confirm",
        headers=_headers(),
        json={"draft_id": draft_id},
    )
    assert r_conf.status_code == 200
    token = r_conf.json()["confirmation_token"]
    payload = _valid_quarterly_payload()
    payload["confirmation_token"] = token
    r_submit = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=payload,
    )
    assert r_submit.status_code == 202
    r_again = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=payload,
    )
    assert r_again.status_code == 403
    assert "already used" in r_again.json()["detail"].lower()


def test_hmrc_mtd_submit_rejects_report_changed_after_confirm(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_REQUIRE_EXPLICIT_CONFIRM", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    report = _valid_quarterly_payload()["report"]
    r_draft = client.post(
        "/integrations/hmrc/mtd/quarterly-update/draft",
        headers=_headers(),
        json={"report": report},
    )
    draft_id = r_draft.json()["draft_id"]
    r_conf = client.post(
        "/integrations/hmrc/mtd/quarterly-update/confirm",
        headers=_headers(),
        json={"draft_id": draft_id},
    )
    token = r_conf.json()["confirmation_token"]
    payload = _valid_quarterly_payload()
    payload["confirmation_token"] = token
    payload["report"]["financials"]["turnover"] = 999999.0
    r_submit = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=payload,
    )
    assert r_submit.status_code == 400
    assert "hash mismatch" in r_submit.json()["detail"].lower()


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


def test_submit_hmrc_mtd_quarterly_rejects_unverified_cis_without_ack(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    body = _valid_quarterly_payload()
    body["report"]["cis_disclosure"] = {
        "credit_verified_gbp": 0.0,
        "credit_self_attested_unverified_gbp": 100.0,
    }
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
    )
    assert response.status_code == 400
    assert "UNVERIFIED CIS" in response.json()["detail"]


def test_submit_hmrc_mtd_quarterly_accepts_unverified_cis_with_ack(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    body = _valid_quarterly_payload()
    body["report"]["cis_disclosure"] = {
        "credit_verified_gbp": 0.0,
        "credit_self_attested_unverified_gbp": 100.0,
    }
    body["unverified_cis_submit_acknowledged"] = True
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
    )
    assert response.status_code == 202
    out = response.json()
    assert out["status"] == "pending"
    assert out["transmission_mode"] == "simulated"


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
    captured: dict[str, object] = {}

    async def _fake_fetch_token(**_kwargs):
        return "fake-access-token"

    async def _fake_post_quarterly(*, fraud_headers=None, **_kwargs):
        captured["fraud_headers"] = fraud_headers
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

    body = _valid_quarterly_payload()
    body["client_context"] = _web_fraud_client_context()
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["transmission_mode"] == "direct"
    assert payload["hmrc_status_code"] == 202
    assert payload["hmrc_receipt_reference"] == "hmrc-direct-submission-id"
    fh = captured.get("fraud_headers") or {}
    assert fh.get("Gov-Client-Connection-Method") == "WEB_APP_VIA_SERVER"


def test_submit_hmrc_mtd_quarterly_update_direct_mode_requires_credentials(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "")

    body = _valid_quarterly_payload()
    body["client_context"] = _web_fraud_client_context()
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
    )

    assert response.status_code == 400
    assert "OAuth credentials are missing" in response.json()["detail"]


def test_submit_hmrc_mtd_quarterly_update_uses_fallback_when_enabled(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_FALLBACK_TO_SIMULATION", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "")
    monkeypatch.setattr("app.main.HMRC_SUBMISSION_EVENTS", deque(maxlen=200))

    body = _valid_quarterly_payload()
    body["client_context"] = _web_fraud_client_context()
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
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
    assert payload["hmrc_environment"] in {"sandbox", "production"}
    assert "hmrc_api_base_url" in payload
    assert "oauth_token_host" in payload
    assert payload["http_max_retries"] >= 1
    assert payload["http_retry_backoff_seconds"] >= 0.0
    assert payload["readiness_band"] in {"ready", "degraded", "not_ready"}


def test_quarterly_report_fingerprint_includes_cis_disclosure():
    from app.hmrc_mtd import (
        HMRCMTDQuarterlyReport,
        compute_quarterly_report_fingerprint,
    )

    base_report = dict(_valid_quarterly_payload()["report"])
    r0 = HMRCMTDQuarterlyReport.model_validate({**base_report, "cis_disclosure": None})
    r1 = HMRCMTDQuarterlyReport.model_validate(
        {
            **base_report,
            "cis_disclosure": {
                "credit_verified_gbp": 10.0,
                "credit_self_attested_unverified_gbp": 0.0,
            },
        }
    )
    r2 = HMRCMTDQuarterlyReport.model_validate(
        {
            **base_report,
            "cis_disclosure": {
                "credit_verified_gbp": 10.0,
                "credit_self_attested_unverified_gbp": 5.0,
            },
        }
    )
    h0 = compute_quarterly_report_fingerprint(r0)
    h1 = compute_quarterly_report_fingerprint(r1)
    h2 = compute_quarterly_report_fingerprint(r2)
    assert h0 != h1
    assert h1 != h2


def test_hmrc_mtd_submit_rejects_cis_disclosure_changed_after_confirm(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_REQUIRE_EXPLICIT_CONFIRM", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    report = dict(_valid_quarterly_payload()["report"])
    report["cis_disclosure"] = {
        "credit_verified_gbp": 100.0,
        "credit_self_attested_unverified_gbp": 0.0,
    }
    r_draft = client.post(
        "/integrations/hmrc/mtd/quarterly-update/draft",
        headers=_headers(),
        json={"report": report},
    )
    assert r_draft.status_code == 201
    draft_id = r_draft.json()["draft_id"]
    r_conf = client.post(
        "/integrations/hmrc/mtd/quarterly-update/confirm",
        headers=_headers(),
        json={"draft_id": draft_id},
    )
    assert r_conf.status_code == 200
    token = r_conf.json()["confirmation_token"]
    payload = _valid_quarterly_payload()
    payload["confirmation_token"] = token
    payload["report"] = {
        **report,
        "cis_disclosure": {
            "credit_verified_gbp": 0.0,
            "credit_self_attested_unverified_gbp": 200.0,
        },
    }
    payload["unverified_cis_submit_acknowledged"] = True
    r_submit = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=payload,
    )
    assert r_submit.status_code == 400
    assert "hash mismatch" in r_submit.json()["detail"].lower()


def test_quarterly_direct_requires_client_context_for_pro(monkeypatch):
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "client-secret")
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(plan="pro", hmrc_direct_submission=True),
        json=_valid_quarterly_payload(),
    )
    assert response.status_code == 400
    assert "client_context" in response.json()["detail"].lower()


def test_quarterly_starter_allows_missing_client_context_when_live_hmrc(monkeypatch):
    async def _fake_fetch_token(**_kwargs):
        return "fake-access-token"

    async def _fake_post_quarterly(*, fraud_headers=None, **_kwargs):
        return httpx.Response(
            202,
            json={"submissionId": "hmrc-starter-id"},
            request=httpx.Request("POST", "https://test-api.service.hmrc.gov.uk/itsa/quarterly-updates"),
        )

    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr("app.hmrc_mtd._fetch_hmrc_oauth_access_token", _fake_fetch_token)
    monkeypatch.setattr("app.hmrc_mtd._post_hmrc_quarterly_update", _fake_post_quarterly)

    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(plan="starter", hmrc_direct_submission=False),
        json=_valid_quarterly_payload(),
    )
    assert response.status_code == 202
    assert response.json()["transmission_mode"] == "direct"


def test_quarterly_direct_mobile_uses_mobile_via_server(monkeypatch):
    captured: dict[str, object] = {}

    async def _fake_fetch_token(**_kwargs):
        return "fake-access-token"

    async def _fake_post_quarterly(*, fraud_headers=None, **_kwargs):
        captured["fraud_headers"] = fraud_headers
        return httpx.Response(
            202,
            json={"submissionId": "hmrc-mob-id"},
            request=httpx.Request("POST", "https://test-api.service.hmrc.gov.uk/itsa/quarterly-updates"),
        )

    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("app.main.HMRC_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr("app.hmrc_mtd._fetch_hmrc_oauth_access_token", _fake_fetch_token)
    monkeypatch.setattr("app.hmrc_mtd._post_hmrc_quarterly_update", _fake_post_quarterly)

    body = _valid_quarterly_payload()
    body["client_context"] = _mobile_fraud_client_context()
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
    )
    assert response.status_code == 202
    fh = captured.get("fraud_headers") or {}
    assert fh.get("Gov-Client-Connection-Method") == "MOBILE_APP_VIA_SERVER"


def test_unverified_cis_ack_posts_compliance_audit(monkeypatch):
    from unittest.mock import AsyncMock

    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    monkeypatch.setattr("app.main.COMPLIANCE_SERVICE_URL", "http://compliance:80")
    audit = AsyncMock(return_value=True)
    monkeypatch.setattr("app.main.post_audit_event", audit)
    body = _valid_quarterly_payload()
    body["report"]["cis_disclosure"] = {
        "credit_verified_gbp": 0.0,
        "credit_self_attested_unverified_gbp": 100.0,
    }
    body["unverified_cis_submit_acknowledged"] = True
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=body,
    )
    assert response.status_code == 202
    assert audit.await_count == 2

    def _call_kwargs(c):
        kw = getattr(c, "kwargs", None)
        if kw:
            return kw
        return c[1] if isinstance(c, tuple) and len(c) > 1 else {}

    actions = {_call_kwargs(c)["action"] for c in audit.await_args_list}
    assert actions == {"cis_unverified_submit_confirmed", "mtd_quarterly_submitted"}
    assert audit.await_args.kwargs["compliance_base_url"] == "http://compliance:80"


def test_quarterly_submit_posts_mtd_compliance_audit(monkeypatch):
    from unittest.mock import AsyncMock

    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    monkeypatch.setattr("app.main.COMPLIANCE_SERVICE_URL", "http://compliance:80")
    audit = AsyncMock(return_value=True)
    monkeypatch.setattr("app.main.post_audit_event", audit)
    response = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=_valid_quarterly_payload(),
    )
    assert response.status_code == 202
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "mtd_quarterly_submitted"
    assert audit.await_args.kwargs["details"]["quarter"] == "Q1"
    assert audit.await_args.kwargs["details"]["correlation_id"] == "corr-123"


def test_final_declaration_posts_mtd_compliance_audit(monkeypatch):
    from unittest.mock import AsyncMock

    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    monkeypatch.setattr("app.main.COMPLIANCE_SERVICE_URL", "http://compliance:80")
    audit = AsyncMock(return_value=True)
    monkeypatch.setattr("app.main.post_audit_event", audit)
    body = {
        "tax_year_start": "2025-04-06",
        "tax_year_end": "2026-04-05",
        "total_income": 50000.0,
        "total_expenses": 10000.0,
        "declaration": "true_and_complete",
    }
    response = client.post(
        "/integrations/hmrc/mtd/final-declaration",
        headers=_headers(),
        json=body,
    )
    assert response.status_code == 202
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "mtd_final_declaration_submitted"
    assert audit.await_args.kwargs["details"]["declaration_status"] == "accepted"


# ---------------------------------------------------------------------------
# New endpoints: submissions list, audit trail, audit event
# ---------------------------------------------------------------------------


def test_list_submissions_empty(monkeypatch, tmp_path):
    """GET /integrations/submissions returns empty list when no submissions exist."""
    _isolated_db(monkeypatch, tmp_path)
    r = client.get("/integrations/submissions", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert "submissions" in body
    assert body["submissions"] == []


def _valid_submit_body() -> dict:
    return {
        "tax_period_start": "2026-04-06",
        "tax_period_end": "2026-07-05",
        "tax_due": 3200.0,
    }


def test_list_submissions_after_submit(monkeypatch, tmp_path):
    """GET /integrations/submissions returns records after a simulated submit."""
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    r = client.post(
        "/integrations/hmrc/submit-tax-return",
        headers=_headers(),
        json=_valid_submit_body(),
    )
    assert r.status_code == 202

    r2 = client.get("/integrations/submissions", headers=_headers())
    assert r2.status_code == 200
    subs = r2.json()["submissions"]
    assert len(subs) == 1
    entry = subs[0]
    assert "submission_id" in entry
    assert entry["status"] in {"pending", "accepted", "simulated"}
    assert "submitted_at" in entry


def test_list_submissions_isolated_per_user(monkeypatch, tmp_path):
    """Submissions are scoped per user — user B sees no data from user A."""
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)
    client.post(
        "/integrations/hmrc/submit-tax-return",
        headers=_headers("user-a@test.com"),
        json=_valid_submit_body(),
    )
    r = client.get("/integrations/submissions", headers=_headers("user-b@test.com"))
    assert r.status_code == 200
    assert r.json()["submissions"] == []


def test_audit_trail_empty(monkeypatch, tmp_path):
    """GET /integrations/audit-trail returns empty events list for a fresh user."""
    _isolated_db(monkeypatch, tmp_path)
    r = client.get("/integrations/audit-trail", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert isinstance(body["events"], list)


def test_audit_trail_populated_after_event_and_submit(monkeypatch, tmp_path):
    """Audit trail includes both fraud-audit events and submission records."""
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)

    # Log a preview event
    r_event = client.post(
        "/integrations/audit/event",
        headers=_headers(),
        json={"stage": "preview", "report_hash": "abc123"},
    )
    assert r_event.status_code == 201
    assert r_event.json()["recorded"] is True

    # Submit a return so there's also a submission_record event
    client.post(
        "/integrations/hmrc/submit-tax-return",
        headers=_headers(),
        json=_valid_submit_body(),
    )

    r_trail = client.get("/integrations/audit-trail", headers=_headers())
    assert r_trail.status_code == 200
    events = r_trail.json()["events"]
    assert len(events) >= 2
    types = {e["event_type"] for e in events}
    assert "preview" in types
    assert "submission_record" in types


def test_audit_event_validates_stage_pattern(monkeypatch, tmp_path):
    """POST /integrations/audit/event rejects stage values with invalid characters."""
    _isolated_db(monkeypatch, tmp_path)
    r = client.post(
        "/integrations/audit/event",
        headers=_headers(),
        json={"stage": "BAD STAGE!!"},
    )
    assert r.status_code == 422


def test_audit_event_confirm_stage(monkeypatch, tmp_path):
    """POST /integrations/audit/event records confirm stage successfully."""
    _isolated_db(monkeypatch, tmp_path)
    r = client.post(
        "/integrations/audit/event",
        headers=_headers(),
        json={"stage": "confirm", "report_hash": "deadbeef00001234"},
    )
    assert r.status_code == 201
    assert r.json()["recorded"] is True

    # Verify it appears in the audit trail
    trail_events = client.get("/integrations/audit-trail", headers=_headers()).json()["events"]
    assert any(e["event_type"] == "confirm" for e in trail_events)


def test_duplicate_confirmation_token_rejected(monkeypatch, tmp_path):
    """Submitting the same confirmation token twice returns 403 on second attempt."""
    _isolated_db(monkeypatch, tmp_path)
    monkeypatch.setattr("app.main.HMRC_REQUIRE_EXPLICIT_CONFIRM", True)
    monkeypatch.setattr("app.main.HMRC_DIRECT_SUBMISSION_ENABLED", False)

    report = _valid_quarterly_payload()["report"]
    draft_id = client.post(
        "/integrations/hmrc/mtd/quarterly-update/draft",
        headers=_headers(),
        json={"report": report},
    ).json()["draft_id"]

    token = client.post(
        "/integrations/hmrc/mtd/quarterly-update/confirm",
        headers=_headers(),
        json={"draft_id": draft_id},
    ).json()["confirmation_token"]

    payload = _valid_quarterly_payload()
    payload["confirmation_token"] = token

    r1 = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=payload,
    )
    assert r1.status_code == 202

    r2 = client.post(
        "/integrations/hmrc/mtd/quarterly-update",
        headers=_headers(),
        json=payload,
    )
    assert r2.status_code == 403
    assert "already used" in r2.json()["detail"].lower()
