import os
import sys
import uuid
import csv
import io
import asyncio
import datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["AUTO_CREATE_SCHEMA"] = "true"

from app import crud, models
from app.database import Base, get_db
from app.main import app

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


def get_auth_headers(
    user_id: str = TEST_USER_ID,
    *,
    scopes: list[str] | None = None,
    roles: list[str] | None = None,
    is_admin: bool = False,
) -> dict[str, str]:
    payload: dict[str, object] = {"sub": user_id}
    if scopes is not None:
        payload["scopes"] = scopes
    if roles is not None:
        payload["roles"] = roles
    payload["is_admin"] = is_admin
    token = jwt.encode(payload, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def get_billing_headers(user_id: str = "billing-admin@example.com") -> dict[str, str]:
    return get_auth_headers(
        user_id,
        scopes=["billing:read"],
        roles=["admin"],
        is_admin=True,
    )


def create_handoff_lead(partner_id: str, user_id: str) -> str:
    response = client.post(f"/partners/{partner_id}/handoff", headers=get_auth_headers(user_id))
    assert response.status_code == 202
    return response.json()["lead_id"]


def set_lead_status(lead_id: str, status_value: str, billing_user: str = "billing-admin@example.com") -> None:
    response = client.patch(
        f"/leads/{lead_id}/status",
        headers=get_billing_headers(billing_user),
        json={"status": status_value},
    )
    assert response.status_code == 200
    assert response.json()["status"] == status_value


async def _set_lead_timestamps(
    lead_id: str,
    *,
    created_days_ago: int,
    updated_days_ago: int,
    status_value: str | None = None,
) -> None:
    now = datetime.datetime.now(datetime.UTC)
    values = {
        "created_at": now - datetime.timedelta(days=created_days_ago),
        "updated_at": now - datetime.timedelta(days=updated_days_ago),
    }
    if status_value is not None:
        values["status"] = status_value
    async with TestingSessionLocal() as session:
        await session.execute(
            update(models.HandoffLead).where(models.HandoffLead.id == lead_id).values(**values)
        )
        await session.commit()


def patch_lead_timestamps(
    lead_id: str,
    *,
    created_days_ago: int,
    updated_days_ago: int,
    status_value: str | None = None,
) -> None:
    asyncio.run(
        _set_lead_timestamps(
            lead_id,
            created_days_ago=created_days_ago,
            updated_days_ago=updated_days_ago,
            status_value=status_value,
        )
    )


async def _set_nps_timestamp(response_id: str, *, created_days_ago: int) -> None:
    now = datetime.datetime.now(datetime.UTC)
    async with TestingSessionLocal() as session:
        await session.execute(
            update(models.NPSResponse)
            .where(models.NPSResponse.id == response_id)
            .values(created_at=now - datetime.timedelta(days=created_days_ago))
        )
        await session.commit()


def patch_nps_timestamp(response_id: str, *, created_days_ago: int) -> None:
    asyncio.run(_set_nps_timestamp(response_id, created_days_ago=created_days_ago))


async def _set_invoice_snapshot(
    invoice_id: str,
    *,
    created_days_ago: int,
    total_amount_gbp: float,
    status_value: str,
) -> None:
    now = datetime.datetime.now(datetime.UTC)
    async with TestingSessionLocal() as session:
        await session.execute(
            update(models.BillingInvoice)
            .where(models.BillingInvoice.id == invoice_id)
            .values(
                created_at=now - datetime.timedelta(days=created_days_ago),
                total_amount_gbp=total_amount_gbp,
                status=status_value,
            )
        )
        await session.commit()


def patch_invoice_snapshot(
    invoice_id: str,
    *,
    created_days_ago: int,
    total_amount_gbp: float,
    status_value: str = "paid",
) -> None:
    asyncio.run(
        _set_invoice_snapshot(
            invoice_id,
            created_days_ago=created_days_ago,
            total_amount_gbp=total_amount_gbp,
            status_value=status_value,
        )
    )


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        await crud.seed_partners_if_empty(session)

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


def test_list_partners_and_filter():
    response = client.get("/partners")
    assert response.status_code == 200
    partners = response.json()
    assert len(partners) == 3

    filter_response = client.get("/partners?service_type=mortgage_advice")
    assert filter_response.status_code == 200
    filtered = filter_response.json()
    assert len(filtered) == 1
    assert filtered[0]["name"] == "HomePath Mortgages"


def test_handoff_triggers_audit(mocker):
    mock_log = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners_response = client.get("/partners")
    partner_id = partners_response.json()[0]["id"]

    handoff_response = client.post(f"/partners/{partner_id}/handoff", headers=get_auth_headers())
    assert handoff_response.status_code == 202
    payload = handoff_response.json()
    assert "Handoff to" in payload["message"]
    assert payload["audit_event_id"] == "audit-1"
    assert payload["duplicated"] is False
    assert uuid.UUID(payload["lead_id"])

    mock_log.assert_awaited_once()
    call_args = mock_log.call_args.kwargs
    assert call_args["user_id"] == TEST_USER_ID
    assert call_args["action"] == "partner.handoff.initiated"
    assert call_args["details"]["partner_id"] == partner_id
    assert uuid.UUID(call_args["details"]["lead_id"])


def test_duplicate_handoff_is_deduplicated(mocker):
    mock_log = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners_response = client.get("/partners")
    partner_id = partners_response.json()[0]["id"]

    first_response = client.post(f"/partners/{partner_id}/handoff", headers=get_auth_headers())
    assert first_response.status_code == 202
    first_payload = first_response.json()
    assert first_payload["duplicated"] is False

    second_response = client.post(f"/partners/{partner_id}/handoff", headers=get_auth_headers())
    assert second_response.status_code == 202
    second_payload = second_response.json()
    assert second_payload["duplicated"] is True
    assert second_payload["lead_id"] == first_payload["lead_id"]

    mock_log.assert_awaited_once()


def test_lead_report_aggregates_by_partner(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners = client.get("/partners").json()
    partner_a = partners[0]["id"]
    partner_b = partners[1]["id"]

    lead_1 = create_handoff_lead(partner_a, "user-a@example.com")
    lead_2 = create_handoff_lead(partner_a, "user-b@example.com")
    lead_3 = create_handoff_lead(partner_b, "user-a@example.com")
    set_lead_status(lead_1, "qualified")
    set_lead_status(lead_2, "qualified")
    set_lead_status(lead_3, "qualified")

    report_response = client.get("/leads/report", headers=get_billing_headers())
    assert report_response.status_code == 200
    payload = report_response.json()

    assert payload["total_leads"] == 3
    assert payload["unique_users"] == 2

    by_partner = {item["partner_id"]: item for item in payload["by_partner"]}
    assert by_partner[partner_a]["leads_count"] == 2
    assert by_partner[partner_a]["unique_users"] == 2
    assert by_partner[partner_b]["leads_count"] == 1
    assert by_partner[partner_b]["unique_users"] == 1


def test_lead_report_supports_partner_filter(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners = client.get("/partners").json()
    partner_a = partners[0]["id"]
    partner_b = partners[1]["id"]

    lead_1 = create_handoff_lead(partner_a, "user-a@example.com")
    lead_2 = create_handoff_lead(partner_b, "user-b@example.com")
    set_lead_status(lead_1, "qualified")
    set_lead_status(lead_2, "qualified")

    report_response = client.get(
        f"/leads/report?partner_id={partner_a}",
        headers=get_billing_headers(),
    )
    assert report_response.status_code == 200
    payload = report_response.json()

    assert payload["total_leads"] == 1
    assert payload["unique_users"] == 1
    assert len(payload["by_partner"]) == 1
    assert payload["by_partner"][0]["partner_id"] == partner_a


def test_lead_report_rejects_invalid_date_range():
    response = client.get(
        "/leads/report?start_date=2026-01-10&end_date=2026-01-01",
        headers=get_billing_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "start_date cannot be after end_date"


def test_lead_report_csv_export(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners = client.get("/partners").json()
    partner_a = partners[0]["id"]
    partner_b = partners[1]["id"]

    lead_1 = create_handoff_lead(partner_a, "user-a@example.com")
    lead_2 = create_handoff_lead(partner_b, "user-b@example.com")
    set_lead_status(lead_1, "qualified")
    set_lead_status(lead_2, "qualified")

    response = client.get("/leads/report.csv", headers=get_billing_headers())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"lead_report_" in response.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["row_type"] == "SUMMARY"
    assert rows[0]["leads_count"] == "2"
    assert rows[0]["unique_users"] == "2"

    partner_rows = [row for row in rows if row["row_type"] == "PARTNER"]
    assert len(partner_rows) == 2
    partner_ids = {row["partner_id"] for row in partner_rows}
    assert partner_a in partner_ids
    assert partner_b in partner_ids


def test_lead_report_csv_via_format_query(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_id = create_handoff_lead(partner_id, "user-a@example.com")
    set_lead_status(lead_id, "qualified")

    response = client.get(
        "/leads/report?format=csv",
        headers=get_billing_headers(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "row_type,period_start,period_end,partner_id,partner_name,leads_count,unique_users" in response.text


def test_lead_report_requires_billing_scope():
    response = client.get("/leads/report", headers=get_auth_headers("user-no-scope@example.com"))
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions for lead reports"


def test_lead_report_allows_admin_claim_without_scope(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    assert client.post(
        f"/partners/{partner_id}/handoff",
        headers=get_auth_headers("user-a@example.com"),
    ).status_code == 202

    response = client.get("/leads/report", headers=get_auth_headers("admin@example.com", is_admin=True))
    assert response.status_code == 200


def test_default_report_includes_only_qualified_leads(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    qualified_lead = create_handoff_lead(partner_id, "user-qualified@example.com")
    create_handoff_lead(partner_id, "user-initiated@example.com")

    set_lead_status(qualified_lead, "qualified")

    response = client.get("/leads/report", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_leads"] == 1
    assert payload["unique_users"] == 1


def test_report_includes_all_statuses_when_billable_disabled(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    create_handoff_lead(partner_id, "user-1@example.com")
    create_handoff_lead(partner_id, "user-2@example.com")

    response = client.get("/leads/report?billable_only=false", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_leads"] == 2
    assert payload["unique_users"] == 2


def test_lead_status_update_rejects_invalid_transition(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_id = create_handoff_lead(partner_id, "user-transition@example.com")

    response = client.patch(
        f"/leads/{lead_id}/status",
        headers=get_billing_headers(),
        json={"status": "converted"},
    )
    assert response.status_code == 409
    assert "Cannot transition lead status" in response.json()["detail"]


def test_billing_report_aggregates_amounts(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_a = create_handoff_lead(partner_id, "billing-user-a@example.com")
    lead_b = create_handoff_lead(partner_id, "billing-user-b@example.com")

    set_lead_status(lead_a, "qualified")
    set_lead_status(lead_b, "qualified")
    set_lead_status(lead_b, "converted")

    response = client.get("/leads/billing", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()

    assert payload["currency"] == "GBP"
    assert payload["total_leads"] == 2
    assert payload["qualified_leads"] == 1
    assert payload["converted_leads"] == 1
    assert payload["total_amount_gbp"] > 0
    assert len(payload["by_partner"]) >= 1


def test_lead_funnel_summary_rates(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_qualified = create_handoff_lead(partner_id, "funnel-qualified@example.com")
    lead_converted = create_handoff_lead(partner_id, "funnel-converted@example.com")
    create_handoff_lead(partner_id, "funnel-initiated@example.com")

    set_lead_status(lead_qualified, "qualified")
    set_lead_status(lead_converted, "qualified")
    set_lead_status(lead_converted, "converted")

    response = client.get("/leads/funnel-summary", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_leads"] == 3
    assert payload["qualified_leads"] == 1
    assert payload["converted_leads"] == 1
    assert payload["qualification_rate_percent"] == 33.3
    assert payload["conversion_rate_from_qualified_percent"] == 100.0
    assert payload["overall_conversion_rate_percent"] == 33.3


def test_seed_readiness_snapshot_returns_investor_kpis(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]

    lead_qualified = create_handoff_lead(partner_id, "seed-qualified@example.com")
    lead_converted = create_handoff_lead(partner_id, "seed-converted@example.com")
    set_lead_status(lead_qualified, "qualified")
    set_lead_status(lead_converted, "qualified")
    set_lead_status(lead_converted, "converted")

    invoice_create = client.post(
        "/billing/invoices/generate",
        headers=get_billing_headers(),
        json={"partner_id": partner_id},
    )
    assert invoice_create.status_code == 201
    invoice_id = invoice_create.json()["id"]
    assert client.patch(
        f"/billing/invoices/{invoice_id}/status",
        headers=get_billing_headers(),
        json={"status": "issued"},
    ).status_code == 200
    assert client.patch(
        f"/billing/invoices/{invoice_id}/status",
        headers=get_billing_headers(),
        json={"status": "paid"},
    ).status_code == 200

    response = client.get("/investor/seed-readiness?period_months=6", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["period_months"] == 6
    assert payload["leads_last_90d"] >= 2
    assert payload["qualified_last_90d"] >= 1
    assert payload["converted_last_90d"] >= 1
    assert payload["current_month_mrr_gbp"] >= 0
    assert payload["active_invoice_count"] >= 1
    assert len(payload["monthly_mrr_series"]) == 6
    assert payload["readiness_band"] in {"early", "progressing", "investable"}
    assert isinstance(payload["next_actions"], list) and len(payload["next_actions"]) >= 1


def test_pmf_evidence_snapshot_returns_activation_and_retention_cohorts(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners = client.get("/partners").json()
    partner_a = partners[0]["id"]
    partner_b = partners[1]["id"]
    partner_c = partners[2]["id"]

    # User A: activated and retained across 30/60/90 windows.
    lead_a1 = create_handoff_lead(partner_a, "pmf-user-a@example.com")
    lead_a2 = create_handoff_lead(partner_b, "pmf-user-a@example.com")
    lead_a3 = create_handoff_lead(partner_c, "pmf-user-a@example.com")
    set_lead_status(lead_a1, "qualified")
    patch_lead_timestamps(
        lead_a1,
        created_days_ago=100,
        updated_days_ago=95,
        status_value="qualified",
    )
    patch_lead_timestamps(
        lead_a2,
        created_days_ago=65,
        updated_days_ago=5,
        status_value="initiated",
    )
    patch_lead_timestamps(
        lead_a3,
        created_days_ago=35,
        updated_days_ago=35,
        status_value="initiated",
    )

    # User B: not activated and not retained.
    lead_b1 = create_handoff_lead(partner_a, "pmf-user-b@example.com")
    patch_lead_timestamps(
        lead_b1,
        created_days_ago=100,
        updated_days_ago=100,
        status_value="initiated",
    )

    # User C: recently activated but not yet eligible for 30/60/90 retention.
    lead_c1 = create_handoff_lead(partner_b, "pmf-user-c@example.com")
    set_lead_status(lead_c1, "qualified")
    patch_lead_timestamps(
        lead_c1,
        created_days_ago=20,
        updated_days_ago=5,
        status_value="qualified",
    )

    response = client.get(
        "/investor/pmf-evidence?cohort_months=6&activation_window_days=30",
        headers=get_billing_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["cohort_months"] == 6
    assert payload["activation_window_days"] == 30
    assert payload["total_new_users"] == 3
    assert payload["activated_users"] == 2
    assert payload["activation_rate_percent"] == 66.7
    assert payload["eligible_users_30d"] == 2
    assert payload["retained_users_30d"] == 1
    assert payload["retention_rate_30d_percent"] == 50.0
    assert payload["eligible_users_60d"] == 2
    assert payload["retained_users_60d"] == 1
    assert payload["retention_rate_60d_percent"] == 50.0
    assert payload["eligible_users_90d"] == 2
    assert payload["retained_users_90d"] == 1
    assert payload["retention_rate_90d_percent"] == 50.0
    assert payload["pmf_band"] in {"early", "emerging", "pmf_confirmed"}
    assert len(payload["monthly_cohorts"]) == 6


def test_nps_submission_and_monthly_trend_reporting(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")

    submit_a = client.post(
        "/investor/nps/responses",
        headers=get_auth_headers("nps-a@example.com"),
        json={"score": 10, "feedback": "Great product flow."},
    )
    submit_b = client.post(
        "/investor/nps/responses",
        headers=get_auth_headers("nps-b@example.com"),
        json={"score": 8, "feedback": "Good, but can improve onboarding."},
    )
    submit_c = client.post(
        "/investor/nps/responses",
        headers=get_auth_headers("nps-c@example.com"),
        json={"score": 4, "feedback": "Too many manual steps."},
    )
    assert submit_a.status_code == 201
    assert submit_b.status_code == 201
    assert submit_c.status_code == 201
    assert submit_a.json()["score_band"] == "promoter"
    assert submit_b.json()["score_band"] == "passive"
    assert submit_c.json()["score_band"] == "detractor"

    patch_nps_timestamp(submit_a.json()["response_id"], created_days_ago=65)
    patch_nps_timestamp(submit_b.json()["response_id"], created_days_ago=35)
    patch_nps_timestamp(submit_c.json()["response_id"], created_days_ago=5)

    forbidden_trend = client.get("/investor/nps/trend", headers=get_auth_headers("nps-a@example.com"))
    assert forbidden_trend.status_code == 403

    trend_response = client.get("/investor/nps/trend?period_months=6", headers=get_billing_headers())
    assert trend_response.status_code == 200
    payload = trend_response.json()
    assert payload["period_months"] == 6
    assert payload["total_responses"] == 3
    assert payload["promoters_count"] == 1
    assert payload["passives_count"] == 1
    assert payload["detractors_count"] == 1
    assert payload["overall_nps_score"] == 0.0
    assert len(payload["monthly_trend"]) == 6


def test_pmf_gate_status_reports_failing_criteria_by_default(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]

    lead_id = create_handoff_lead(partner_id, "gate-user@example.com")
    set_lead_status(lead_id, "qualified")
    patch_lead_timestamps(lead_id, created_days_ago=40, updated_days_ago=35, status_value="qualified")

    nps_submit = client.post(
        "/investor/nps/responses",
        headers=get_auth_headers("gate-user@example.com"),
        json={"score": 10},
    )
    assert nps_submit.status_code == 201
    patch_nps_timestamp(nps_submit.json()["response_id"], created_days_ago=5)

    response = client.get("/investor/pmf-gate", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["gate_name"] == "seed_pmf_gate_v1"
    assert payload["gate_passed"] is False
    assert payload["sample_size_passed"] is False
    assert isinstance(payload["next_actions"], list) and len(payload["next_actions"]) >= 1


def test_pmf_gate_status_can_pass_when_thresholds_are_met(mocker, monkeypatch):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners = client.get("/partners").json()
    partner_a = partners[0]["id"]
    partner_b = partners[1]["id"]
    partner_c = partners[2]["id"]

    # Build 4-user cohort: 3 activated (75%), 3 retained at 90d (75%).
    lead_a = create_handoff_lead(partner_a, "gate-a@example.com")
    lead_a2 = create_handoff_lead(partner_b, "gate-a@example.com")
    lead_a3 = create_handoff_lead(partner_c, "gate-a@example.com")
    set_lead_status(lead_a, "qualified")
    patch_lead_timestamps(lead_a, created_days_ago=120, updated_days_ago=110, status_value="qualified")
    patch_lead_timestamps(lead_a2, created_days_ago=92, updated_days_ago=5, status_value="initiated")
    patch_lead_timestamps(lead_a3, created_days_ago=35, updated_days_ago=35, status_value="initiated")

    lead_b = create_handoff_lead(partner_a, "gate-b@example.com")
    lead_b2 = create_handoff_lead(partner_b, "gate-b@example.com")
    set_lead_status(lead_b, "qualified")
    patch_lead_timestamps(lead_b, created_days_ago=120, updated_days_ago=110, status_value="qualified")
    patch_lead_timestamps(lead_b2, created_days_ago=95, updated_days_ago=7, status_value="initiated")

    lead_c = create_handoff_lead(partner_a, "gate-c@example.com")
    lead_c2 = create_handoff_lead(partner_b, "gate-c@example.com")
    set_lead_status(lead_c, "qualified")
    patch_lead_timestamps(lead_c, created_days_ago=120, updated_days_ago=110, status_value="qualified")
    patch_lead_timestamps(lead_c2, created_days_ago=96, updated_days_ago=8, status_value="initiated")

    lead_d = create_handoff_lead(partner_a, "gate-d@example.com")
    patch_lead_timestamps(lead_d, created_days_ago=120, updated_days_ago=120, status_value="initiated")

    # NPS responses: 3 promoters, 1 detractor => overall NPS = 50.
    scores_by_user = {
        "gate-a@example.com": 10,
        "gate-b@example.com": 9,
        "gate-c@example.com": 9,
        "gate-d@example.com": 4,
    }
    for user_id, score in scores_by_user.items():
        submit = client.post(
            "/investor/nps/responses",
            headers=get_auth_headers(user_id),
            json={"score": score},
        )
        assert submit.status_code == 201
        patch_nps_timestamp(submit.json()["response_id"], created_days_ago=10)

    monkeypatch.setattr("app.main.PMF_GATE_REQUIRED_ACTIVATION_RATE_PERCENT", 60.0)
    monkeypatch.setattr("app.main.PMF_GATE_REQUIRED_RETENTION_90D_PERCENT", 75.0)
    monkeypatch.setattr("app.main.PMF_GATE_REQUIRED_NPS_SCORE", 45.0)
    monkeypatch.setattr("app.main.PMF_GATE_MIN_ELIGIBLE_USERS_90D", 4)
    monkeypatch.setattr("app.main.PMF_GATE_MIN_NPS_RESPONSES", 4)

    response = client.get("/investor/pmf-gate", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["activation_rate_percent"] == 75.0
    assert payload["retention_rate_90d_percent"] == 75.0
    assert payload["overall_nps_score"] == 50.0
    assert payload["eligible_users_90d"] == 4
    assert payload["total_nps_responses"] == 4
    assert payload["activation_passed"] is True
    assert payload["retention_passed"] is True
    assert payload["nps_passed"] is True
    assert payload["sample_size_passed"] is True
    assert payload["gate_passed"] is True


def test_investor_snapshot_export_supports_json_and_csv(mocker, monkeypatch):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_id = create_handoff_lead(partner_id, "snapshot-user@example.com")
    set_lead_status(lead_id, "qualified")
    patch_lead_timestamps(lead_id, created_days_ago=45, updated_days_ago=40, status_value="qualified")

    nps_submit = client.post(
        "/investor/nps/responses",
        headers=get_auth_headers("snapshot-user@example.com"),
        json={"score": 9},
    )
    assert nps_submit.status_code == 201
    patch_nps_timestamp(nps_submit.json()["response_id"], created_days_ago=5)

    monkeypatch.setattr("app.main.PMF_GATE_MIN_ELIGIBLE_USERS_90D", 1)
    monkeypatch.setattr("app.main.PMF_GATE_MIN_NPS_RESPONSES", 1)

    json_response = client.get("/investor/snapshot/export?format=json", headers=get_billing_headers())
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["seed_readiness"]["period_months"] == 6
    assert payload["pmf_evidence"]["cohort_months"] == 6
    assert "overall_nps_score" in payload["nps_trend"]
    assert payload["pmf_gate"]["gate_name"] == "seed_pmf_gate_v1"
    assert "unit_economics" in payload

    csv_response = client.get("/investor/snapshot/export?format=csv", headers=get_billing_headers())
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "investor_snapshot.csv" in csv_response.headers["content-disposition"]
    assert "section,metric,value" in csv_response.text
    assert "pmf_gate,gate_passed" in csv_response.text


def test_marketing_spend_ingestion_and_unit_economics_seed_gate(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    today = datetime.datetime.now(datetime.UTC).date()
    current_month_mid = today.replace(day=15)
    prev_month_last_day = today.replace(day=1) - datetime.timedelta(days=1)
    previous_month_mid = prev_month_last_day.replace(day=15)

    lead_a = create_handoff_lead(partner_id, "ue-user-a@example.com")
    lead_b = create_handoff_lead(partner_id, "ue-user-b@example.com")
    set_lead_status(lead_a, "qualified")
    set_lead_status(lead_b, "qualified")

    invoice_prev = client.post(
        "/billing/invoices/generate",
        headers=get_billing_headers(),
        json={"partner_id": partner_id},
    )
    invoice_curr = client.post(
        "/billing/invoices/generate",
        headers=get_billing_headers(),
        json={"partner_id": partner_id},
    )
    assert invoice_prev.status_code == 201
    assert invoice_curr.status_code == 201
    patch_invoice_snapshot(
        invoice_prev.json()["id"],
        created_days_ago=20,
        total_amount_gbp=50000.0,
        status_value="paid",
    )
    patch_invoice_snapshot(
        invoice_curr.json()["id"],
        created_days_ago=2,
        total_amount_gbp=51000.0,
        status_value="paid",
    )

    marketing_prev = client.post(
        "/investor/marketing-spend",
        headers=get_billing_headers(),
        json={
            "month_start": previous_month_mid.isoformat(),
            "channel": "Paid Search",
            "spend_gbp": 4500.0,
            "acquired_customers": 120,
        },
    )
    marketing_curr = client.post(
        "/investor/marketing-spend",
        headers=get_billing_headers(),
        json={
            "month_start": current_month_mid.isoformat(),
            "channel": "Partner Referrals",
            "spend_gbp": 4800.0,
            "acquired_customers": 130,
        },
    )
    assert marketing_prev.status_code == 201
    assert marketing_curr.status_code == 201
    assert marketing_prev.json()["month_start"].endswith("-01")

    response = client.get("/investor/unit-economics?period_months=6", headers=get_billing_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["period_months"] == 6
    assert payload["current_month_mrr_gbp"] >= 51000.0
    assert payload["monthly_churn_rate_percent"] < payload["required_max_monthly_churn_percent"]
    assert payload["average_cac_gbp"] is not None
    assert payload["ltv_cac_ratio"] is not None
    assert payload["seed_gate_passed"] is True
    assert len(payload["monthly_points"]) == 6


def test_billing_csv_export_contains_totals(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_id = create_handoff_lead(partner_id, "csv-billing-user@example.com")
    set_lead_status(lead_id, "qualified")

    response = client.get("/leads/billing.csv", headers=get_billing_headers())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "lead_billing_report_" in response.headers["content-disposition"]
    assert "row_type,period_start,period_end,currency,partner_id,partner_name" in response.text
    assert "SUMMARY" in response.text


def test_billing_report_rejects_non_billable_status_filter():
    response = client.get(
        "/leads/billing?statuses=initiated",
        headers=get_billing_headers(),
    )
    assert response.status_code == 400
    assert "supports only qualified/converted statuses" in response.json()["detail"]


def test_update_partner_pricing():
    partner = client.get("/partners").json()[0]
    partner_id = partner["id"]

    response = client.patch(
        f"/partners/{partner_id}/pricing",
        headers=get_billing_headers(),
        json={
            "qualified_lead_fee_gbp": 21.5,
            "converted_lead_fee_gbp": 67.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == partner_id
    assert payload["qualified_lead_fee_gbp"] == 21.5
    assert payload["converted_lead_fee_gbp"] == 67.0


def test_list_leads_supports_filters(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead_a = create_handoff_lead(partner_id, "lead-filter-a@example.com")
    create_handoff_lead(partner_id, "lead-filter-b@example.com")
    set_lead_status(lead_a, "qualified")

    response = client.get(
        "/leads?status=qualified&limit=10&offset=0",
        headers=get_billing_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["status"] == "qualified"
    assert payload["items"][0]["partner_id"] == partner_id


def test_generate_list_and_get_invoice(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead = create_handoff_lead(partner_id, "invoice-user@example.com")
    set_lead_status(lead, "qualified")

    create_response = client.post(
        "/billing/invoices/generate",
        headers=get_billing_headers(),
        json={
            "partner_id": partner_id,
            "statuses": ["qualified"],
        },
    )
    assert create_response.status_code == 201
    invoice_payload = create_response.json()
    invoice_id = invoice_payload["id"]
    assert invoice_payload["status"] == "generated"
    assert invoice_payload["invoice_number"].startswith("INV-")
    assert invoice_payload["due_date"]
    assert invoice_payload["total_amount_gbp"] > 0
    assert len(invoice_payload["lines"]) == 1

    list_response = client.get("/billing/invoices", headers=get_billing_headers())
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] >= 1
    ids = [item["id"] for item in listed["items"]]
    assert invoice_id in ids
    matching = [item for item in listed["items"] if item["id"] == invoice_id][0]
    assert matching["invoice_number"] == invoice_payload["invoice_number"]
    assert matching["due_date"] == invoice_payload["due_date"]

    get_response = client.get(f"/billing/invoices/{invoice_id}", headers=get_billing_headers())
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["id"] == invoice_id
    assert detail["invoice_number"] == invoice_payload["invoice_number"]
    assert detail["lines"][0]["partner_id"] == partner_id


def test_invoice_status_lifecycle_and_invalid_transition(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead = create_handoff_lead(partner_id, "invoice-status-user@example.com")
    set_lead_status(lead, "qualified")

    create_response = client.post(
        "/billing/invoices/generate",
        headers=get_billing_headers(),
        json={"partner_id": partner_id},
    )
    assert create_response.status_code == 201
    invoice_id = create_response.json()["id"]

    issued_response = client.patch(
        f"/billing/invoices/{invoice_id}/status",
        headers=get_billing_headers(),
        json={"status": "issued"},
    )
    assert issued_response.status_code == 200
    assert issued_response.json()["status"] == "issued"

    paid_response = client.patch(
        f"/billing/invoices/{invoice_id}/status",
        headers=get_billing_headers(),
        json={"status": "paid"},
    )
    assert paid_response.status_code == 200
    assert paid_response.json()["status"] == "paid"

    invalid_response = client.patch(
        f"/billing/invoices/{invoice_id}/status",
        headers=get_billing_headers(),
        json={"status": "issued"},
    )
    assert invalid_response.status_code == 409
    assert "Cannot transition invoice status" in invalid_response.json()["detail"]


def test_invoice_pdf_and_accounting_exports(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partner_id = client.get("/partners").json()[0]["id"]
    lead = create_handoff_lead(partner_id, "invoice-export-user@example.com")
    set_lead_status(lead, "qualified")

    create_response = client.post(
        "/billing/invoices/generate",
        headers=get_billing_headers(),
        json={"partner_id": partner_id},
    )
    assert create_response.status_code == 201
    invoice_payload = create_response.json()
    invoice_id = invoice_payload["id"]

    pdf_response = client.get(f"/billing/invoices/{invoice_id}/pdf", headers=get_billing_headers())
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert f"{invoice_payload['invoice_number']}.pdf" in pdf_response.headers["content-disposition"]
    assert pdf_response.content.startswith(b"%PDF-")

    xero_response = client.get(
        f"/billing/invoices/{invoice_id}/accounting.csv?target=xero",
        headers=get_billing_headers(),
    )
    assert xero_response.status_code == 200
    assert xero_response.headers["content-type"].startswith("text/csv")
    assert "ContactName,InvoiceNumber,InvoiceDate,DueDate" in xero_response.text
    assert invoice_payload["invoice_number"] in xero_response.text

    qb_response = client.get(
        f"/billing/invoices/{invoice_id}/accounting.csv?target=quickbooks",
        headers=get_billing_headers(),
    )
    assert qb_response.status_code == 200
    assert qb_response.headers["content-type"].startswith("text/csv")
    assert "Customer,InvoiceNo,InvoiceDate,DueDate" in qb_response.text
    assert invoice_payload["invoice_number"] in qb_response.text


def test_self_employed_invoice_lifecycle_and_exports(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    owner_headers = get_auth_headers("freelancer-owner@example.com")
    other_headers = get_auth_headers("other-user@example.com")

    create_response = client.post(
        "/self-employed/invoices",
        headers=owner_headers,
        json={
            "customer_name": "Acme Client Ltd",
            "customer_email": "accounts@acme-client.example",
            "customer_phone": "+447700900111",
            "customer_address": "10 High Street, London",
            "tax_rate_percent": 20,
            "notes": "Thank you for your business.",
            "lines": [
                {"description": "Consulting services", "quantity": 2, "unit_price_gbp": 150},
                {"description": "Report package", "quantity": 1, "unit_price_gbp": 50},
            ],
        },
    )
    assert create_response.status_code == 201
    invoice_payload = create_response.json()
    invoice_id = invoice_payload["id"]
    assert invoice_payload["invoice_number"].startswith("SEI-")
    assert invoice_payload["status"] == "draft"
    assert invoice_payload["customer_phone"] == "+447700900111"
    assert invoice_payload["subtotal_gbp"] == 350.0
    assert invoice_payload["tax_amount_gbp"] == 70.0
    assert invoice_payload["total_amount_gbp"] == 420.0
    assert invoice_payload["payment_link_url"].startswith("https://pay.selfmonitor.app/invoices/")
    assert invoice_payload["payment_link_provider"] == "selfmonitor_payment_link"
    assert len(invoice_payload["lines"]) == 2

    list_response = client.get("/self-employed/invoices", headers=owner_headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == invoice_id

    get_response = client.get(f"/self-employed/invoices/{invoice_id}", headers=owner_headers)
    assert get_response.status_code == 200
    assert get_response.json()["invoice_number"] == invoice_payload["invoice_number"]

    hidden_response = client.get(f"/self-employed/invoices/{invoice_id}", headers=other_headers)
    assert hidden_response.status_code == 404

    issued_response = client.patch(
        f"/self-employed/invoices/{invoice_id}/status",
        headers=owner_headers,
        json={"status": "issued"},
    )
    assert issued_response.status_code == 200
    assert issued_response.json()["status"] == "issued"

    paid_response = client.patch(
        f"/self-employed/invoices/{invoice_id}/status",
        headers=owner_headers,
        json={"status": "paid"},
    )
    assert paid_response.status_code == 200
    assert paid_response.json()["status"] == "paid"

    invalid_transition = client.patch(
        f"/self-employed/invoices/{invoice_id}/status",
        headers=owner_headers,
        json={"status": "issued"},
    )
    assert invalid_transition.status_code == 409
    assert "Cannot transition self-employed invoice status" in invalid_transition.json()["detail"]

    pdf_response = client.get(f"/self-employed/invoices/{invoice_id}/pdf", headers=owner_headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert pdf_response.content.startswith(b"%PDF-")

    csv_response = client.get(f"/self-employed/invoices/{invoice_id}/csv", headers=owner_headers)
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert invoice_payload["invoice_number"] in csv_response.text


def test_self_employed_invoice_rejects_invalid_due_date(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    response = client.post(
        "/self-employed/invoices",
        headers=get_auth_headers("freelancer-invalid@example.com"),
        json={
            "customer_name": "Invalid Due Date Client",
            "issue_date": "2026-02-20",
            "due_date": "2026-02-19",
            "lines": [{"description": "Service", "quantity": 1, "unit_price_gbp": 100}],
        },
    )
    assert response.status_code == 400
    assert "due_date cannot be earlier than issue_date" in response.json()["detail"]


def test_self_employed_advanced_recurring_branding_and_reminders(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    owner_headers = get_auth_headers("freelancer-advanced@example.com")

    brand_response = client.put(
        "/self-employed/invoicing/brand",
        headers=owner_headers,
        json={
            "business_name": "North Star Consulting",
            "logo_url": "https://assets.example.com/logo.png",
            "accent_color": "#2244AA",
            "payment_terms_note": "Payment due within 14 days.",
        },
    )
    assert brand_response.status_code == 200
    assert brand_response.json()["business_name"] == "North Star Consulting"

    recurring_create = client.post(
        "/self-employed/invoicing/recurring-plans",
        headers=owner_headers,
        json={
            "customer_name": "Repeat Client Ltd",
            "customer_email": "billing@repeat.example",
            "currency": "GBP",
            "tax_rate_percent": 20,
            "cadence": "monthly",
            "next_issue_date": "2026-01-01",
            "lines": [{"description": "Monthly bookkeeping", "quantity": 1, "unit_price_gbp": 120}],
        },
    )
    assert recurring_create.status_code == 201
    recurring_plan_id = recurring_create.json()["id"]
    assert recurring_create.json()["active"] is True

    run_due_response = client.post("/self-employed/invoicing/recurring-plans/run-due", headers=owner_headers)
    assert run_due_response.status_code == 200
    run_due_payload = run_due_response.json()
    assert run_due_payload["generated_count"] == 1
    generated_invoice_id = run_due_payload["generated"][0]["invoice_id"]

    generated_invoice_response = client.get(
        f"/self-employed/invoices/{generated_invoice_id}",
        headers=owner_headers,
    )
    assert generated_invoice_response.status_code == 200
    generated_invoice = generated_invoice_response.json()
    assert generated_invoice["recurring_plan_id"] == recurring_plan_id
    assert generated_invoice["brand_business_name"] == "North Star Consulting"
    assert generated_invoice["brand_accent_color"] == "#2244AA"
    assert generated_invoice["payment_link_url"].startswith("https://pay.selfmonitor.app/invoices/")

    issue_generated = client.patch(
        f"/self-employed/invoices/{generated_invoice_id}/status",
        headers=owner_headers,
        json={"status": "issued"},
    )
    assert issue_generated.status_code == 200
    assert issue_generated.json()["status"] == "issued"

    overdue_candidate_create = client.post(
        "/self-employed/invoices",
        headers=owner_headers,
        json={
            "customer_name": "Late Payer Ltd",
            "issue_date": "2026-01-10",
            "due_date": "2026-01-15",
            "lines": [{"description": "One-off project", "quantity": 1, "unit_price_gbp": 200}],
        },
    )
    assert overdue_candidate_create.status_code == 201
    overdue_invoice_id = overdue_candidate_create.json()["id"]

    issued_overdue_candidate = client.patch(
        f"/self-employed/invoices/{overdue_invoice_id}/status",
        headers=owner_headers,
        json={"status": "issued"},
    )
    assert issued_overdue_candidate.status_code == 200

    invoice_list = client.get("/self-employed/invoices", headers=owner_headers)
    assert invoice_list.status_code == 200
    listed_by_id = {item["id"]: item for item in invoice_list.json()["items"]}
    assert listed_by_id[overdue_invoice_id]["status"] == "overdue"

    reminders_run = client.post(
        "/self-employed/invoicing/reminders/run?due_in_days=30",
        headers=owner_headers,
    )
    assert reminders_run.status_code == 200
    reminders_payload = reminders_run.json()
    assert reminders_payload["reminders_sent_count"] >= 2
    reminder_types = {item["reminder_type"] for item in reminders_payload["reminders"]}
    assert "due_soon" in reminder_types
    assert "overdue" in reminder_types

    reminders_list = client.get("/self-employed/invoicing/reminders", headers=owner_headers)
    assert reminders_list.status_code == 200
    assert reminders_list.json()["total"] >= reminders_payload["reminders_sent_count"]

    recurring_list = client.get("/self-employed/invoicing/recurring-plans", headers=owner_headers)
    assert recurring_list.status_code == 200
    assert recurring_list.json()["total"] == 1
    assert recurring_list.json()["items"][0]["id"] == recurring_plan_id

    pause_plan = client.patch(
        f"/self-employed/invoicing/recurring-plans/{recurring_plan_id}",
        headers=owner_headers,
        json={"active": False},
    )
    assert pause_plan.status_code == 200
    assert pause_plan.json()["active"] is False


def test_self_employed_reminders_dispatch_email_and_sms_channels(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_EMAIL_ENABLED", True)
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_ENABLED", True)
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER", "webhook")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_PROVIDER", "webhook")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_EMAIL_DISPATCH_URL", "http://dispatch.local/email")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_DISPATCH_URL", "http://dispatch.local/sms")
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_dispatch = mocker.patch("app.main._post_with_delivery_retry", new_callable=mocker.AsyncMock, return_value=mock_response)

    owner_headers = get_auth_headers("freelancer-dispatch@example.com")
    today = datetime.datetime.now(datetime.UTC).date()
    create_response = client.post(
        "/self-employed/invoices",
        headers=owner_headers,
        json={
            "customer_name": "Dispatch Client",
            "customer_email": "billing@dispatch-client.example",
            "customer_phone": "+447700900222",
            "issue_date": today.isoformat(),
            "due_date": (today + datetime.timedelta(days=1)).isoformat(),
            "lines": [{"description": "Dispatch test service", "quantity": 1, "unit_price_gbp": 90}],
        },
    )
    assert create_response.status_code == 201
    invoice_id = create_response.json()["id"]

    issued_response = client.patch(
        f"/self-employed/invoices/{invoice_id}/status",
        headers=owner_headers,
        json={"status": "issued"},
    )
    assert issued_response.status_code == 200

    reminders_run = client.post(
        "/self-employed/invoicing/reminders/run?due_in_days=7",
        headers=owner_headers,
    )
    assert reminders_run.status_code == 200
    reminder_payload = reminders_run.json()
    channels = {item["channel"] for item in reminder_payload["reminders"]}
    assert {"in_app", "email", "sms"}.issubset(channels)
    assert mock_dispatch.await_count == 2

    called_urls = {call.args[0] for call in mock_dispatch.await_args_list}
    assert "http://dispatch.local/email" in called_urls
    assert "http://dispatch.local/sms" in called_urls


def test_self_employed_reminders_dispatch_sendgrid_provider(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_EMAIL_ENABLED", True)
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_ENABLED", False)
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_EMAIL_PROVIDER", "sendgrid")
    mocker.patch("app.main.SELF_EMPLOYED_SENDGRID_API_KEY", "SG.TEST_KEY")
    mocker.patch("app.main.SELF_EMPLOYED_SENDGRID_API_URL", "https://api.sendgrid.com/v3/mail/send")
    mock_response = mocker.Mock()
    mock_response.status_code = 202
    mock_dispatch = mocker.patch("app.main._post_with_delivery_retry", new_callable=mocker.AsyncMock, return_value=mock_response)

    owner_headers = get_auth_headers("freelancer-sendgrid@example.com")
    today = datetime.datetime.now(datetime.UTC).date()
    create_response = client.post(
        "/self-employed/invoices",
        headers=owner_headers,
        json={
            "customer_name": "SendGrid Client",
            "customer_email": "billing@sendgrid-client.example",
            "issue_date": today.isoformat(),
            "due_date": (today + datetime.timedelta(days=1)).isoformat(),
            "lines": [{"description": "Service", "quantity": 1, "unit_price_gbp": 100}],
        },
    )
    assert create_response.status_code == 201
    invoice_id = create_response.json()["id"]
    assert (
        client.patch(
            f"/self-employed/invoices/{invoice_id}/status",
            headers=owner_headers,
            json={"status": "issued"},
        ).status_code
        == 200
    )

    run_response = client.post("/self-employed/invoicing/reminders/run?due_in_days=7", headers=owner_headers)
    assert run_response.status_code == 200
    channels = {item["channel"] for item in run_response.json()["reminders"]}
    assert {"in_app", "email"}.issubset(channels)
    assert mock_dispatch.await_count == 1
    dispatch_call = mock_dispatch.await_args_list[0]
    assert dispatch_call.args[0] == "https://api.sendgrid.com/v3/mail/send"
    assert dispatch_call.kwargs["headers"]["Authorization"].startswith("Bearer ")


def test_self_employed_reminders_dispatch_twilio_provider(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_EMAIL_ENABLED", False)
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_ENABLED", True)
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_PROVIDER", "twilio")
    mocker.patch("app.main.SELF_EMPLOYED_TWILIO_ACCOUNT_SID", "AC_TEST_SID")
    mocker.patch("app.main.SELF_EMPLOYED_TWILIO_AUTH_TOKEN", "TEST_TOKEN")
    mocker.patch("app.main.SELF_EMPLOYED_TWILIO_MESSAGING_SERVICE_SID", "")
    mocker.patch("app.main.SELF_EMPLOYED_REMINDER_SMS_FROM", "+447000000000")
    mocker.patch("app.main.SELF_EMPLOYED_TWILIO_API_BASE_URL", "https://api.twilio.com")
    mock_response = mocker.Mock()
    mock_response.status_code = 201
    mock_dispatch = mocker.patch("app.main._post_with_delivery_retry", new_callable=mocker.AsyncMock, return_value=mock_response)

    owner_headers = get_auth_headers("freelancer-twilio@example.com")
    today = datetime.datetime.now(datetime.UTC).date()
    create_response = client.post(
        "/self-employed/invoices",
        headers=owner_headers,
        json={
            "customer_name": "Twilio Client",
            "customer_phone": "+447700900333",
            "issue_date": today.isoformat(),
            "due_date": (today + datetime.timedelta(days=1)).isoformat(),
            "lines": [{"description": "Service", "quantity": 1, "unit_price_gbp": 100}],
        },
    )
    assert create_response.status_code == 201
    invoice_id = create_response.json()["id"]
    assert (
        client.patch(
            f"/self-employed/invoices/{invoice_id}/status",
            headers=owner_headers,
            json={"status": "issued"},
        ).status_code
        == 200
    )

    run_response = client.post("/self-employed/invoicing/reminders/run?due_in_days=7", headers=owner_headers)
    assert run_response.status_code == 200
    channels = {item["channel"] for item in run_response.json()["reminders"]}
    assert {"in_app", "sms"}.issubset(channels)
    assert mock_dispatch.await_count == 1
    dispatch_call = mock_dispatch.await_args_list[0]
    assert "api.twilio.com/2010-04-01/Accounts/AC_TEST_SID/Messages.json" in dispatch_call.args[0]
    assert dispatch_call.kwargs["form_body"]["To"] == "+447700900333"

