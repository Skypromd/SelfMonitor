import os
import sys
import uuid

from fastapi.testclient import TestClient
from jose import jwt

TEST_DB_PATH = "/tmp/partner_registry_service_test.db"
os.environ["PARTNER_DB_PATH"] = TEST_DB_PATH
os.environ["AUTH_SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app, reset_partner_db_for_tests  # noqa: E402

TEST_AUTH_SECRET = "test-secret"
TEST_AUTH_ALGORITHM = "HS256"
client = TestClient(app)


def auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    reset_partner_db_for_tests()


def test_initiate_handoff_persists_record(mocker):
    user_id = "partner-user@example.com"
    partners_response = client.get("/partners")
    assert partners_response.status_code == 200
    partner_id = partners_response.json()[0]["id"]

    mock_log = mocker.patch("app.main.log_audit_event", new_callable=mocker.AsyncMock)
    mock_log.return_value = "audit-evt-1"

    response = client.post(
        f"/partners/{partner_id}/handoff",
        headers=auth_headers(user_id),
    )
    assert response.status_code == 202
    payload = response.json()
    assert uuid.UUID(payload["handoff_id"])
    assert payload["audit_event_id"] == "audit-evt-1"

    my_handoffs = client.get("/handoffs", headers=auth_headers(user_id))
    assert my_handoffs.status_code == 200
    handoffs = my_handoffs.json()
    assert len(handoffs) == 1
    assert handoffs[0]["partner_id"] == partner_id


def test_handoffs_are_user_scoped():
    response = client.get("/handoffs", headers=auth_headers("new-user@example.com"))
    assert response.status_code == 200
    assert response.json() == []
