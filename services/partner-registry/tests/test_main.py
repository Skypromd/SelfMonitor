import os
import sys
import uuid
import csv
import io

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["AUTO_CREATE_SCHEMA"] = "true"

from app import crud
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

