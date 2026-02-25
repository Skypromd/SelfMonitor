import os
import sys
import time
import uuid

from fastapi.testclient import TestClient
from jose import jwt

TEST_DB_PATH = "/tmp/integrations_service_test.db"
os.environ["INTEGRATIONS_DB_PATH"] = TEST_DB_PATH
os.environ["INTEGRATIONS_PROCESSING_DELAY_SECONDS"] = "0.01"
os.environ["AUTH_SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app, reset_integrations_db_for_tests  # noqa: E402

TEST_AUTH_SECRET = "test-secret"
TEST_AUTH_ALGORITHM = "HS256"
client = TestClient(app)


def auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    reset_integrations_db_for_tests()


def test_submit_and_retrieve_hmrc_submission():
    user_id = "integration-user@example.com"
    submit_response = client.post(
        "/integrations/hmrc/submit-tax-return",
        headers=auth_headers(user_id),
        json={
            "tax_period_start": "2025-04-06",
            "tax_period_end": "2026-04-05",
            "tax_due": 1234.56,
        },
    )
    assert submit_response.status_code == 202
    payload = submit_response.json()
    submission_id = payload["submission_id"]
    assert uuid.UUID(submission_id)

    status_payload = payload
    for _ in range(20):
        status_response = client.get(
            f"/integrations/hmrc/submissions/{submission_id}",
            headers=auth_headers(user_id),
        )
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload["status"] == "completed":
            break
        time.sleep(0.01)

    assert status_payload["status"] == "completed"
    assert status_payload["provider_reference"].startswith("hmrc-")


def test_submission_visibility_is_user_scoped():
    owner = "owner@example.com"
    other = "other@example.com"
    submit_response = client.post(
        "/integrations/hmrc/submit-tax-return",
        headers=auth_headers(owner),
        json={
            "tax_period_start": "2025-04-06",
            "tax_period_end": "2026-04-05",
            "tax_due": 300.0,
        },
    )
    submission_id = submit_response.json()["submission_id"]

    unauthorized_get = client.get(
        f"/integrations/hmrc/submissions/{submission_id}",
        headers=auth_headers(other),
    )
    assert unauthorized_get.status_code == 404
