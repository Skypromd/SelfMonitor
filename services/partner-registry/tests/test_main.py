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

from app import crud
from app.database import Base, get_db
from app.main import app

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
TEST_USER_ID = "test-user@example.com"
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


def get_auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


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

    assert client.post(f"/partners/{partner_a}/handoff", headers=get_auth_headers("user-a@example.com")).status_code == 202
    assert client.post(f"/partners/{partner_a}/handoff", headers=get_auth_headers("user-b@example.com")).status_code == 202
    assert client.post(f"/partners/{partner_b}/handoff", headers=get_auth_headers("user-a@example.com")).status_code == 202

    report_response = client.get("/leads/report", headers=get_auth_headers("billing-admin@example.com"))
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

    assert client.post(f"/partners/{partner_a}/handoff", headers=get_auth_headers("user-a@example.com")).status_code == 202
    assert client.post(f"/partners/{partner_b}/handoff", headers=get_auth_headers("user-b@example.com")).status_code == 202

    report_response = client.get(
        f"/leads/report?partner_id={partner_a}",
        headers=get_auth_headers("billing-admin@example.com"),
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
        headers=get_auth_headers("billing-admin@example.com"),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "start_date cannot be after end_date"


def test_lead_report_csv_export(mocker):
    mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock, return_value="audit-1")
    partners = client.get("/partners").json()
    partner_a = partners[0]["id"]
    partner_b = partners[1]["id"]

    assert client.post(
        f"/partners/{partner_a}/handoff",
        headers=get_auth_headers("user-a@example.com"),
    ).status_code == 202
    assert client.post(
        f"/partners/{partner_b}/handoff",
        headers=get_auth_headers("user-b@example.com"),
    ).status_code == 202

    response = client.get("/leads/report.csv", headers=get_auth_headers("billing-admin@example.com"))
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
    assert client.post(
        f"/partners/{partner_id}/handoff",
        headers=get_auth_headers("user-a@example.com"),
    ).status_code == 202

    response = client.get(
        "/leads/report?format=csv",
        headers=get_auth_headers("billing-admin@example.com"),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "row_type,period_start,period_end,partner_id,partner_name,leads_count,unique_users" in response.text

