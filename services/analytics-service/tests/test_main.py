import os
import sys
import time
import uuid

from fastapi.testclient import TestClient
from jose import jwt

TEST_DB_PATH = "/tmp/analytics_service_test.db"
os.environ["ANALYTICS_DB_PATH"] = TEST_DB_PATH
os.environ["ANALYTICS_JOB_DURATION_SECONDS"] = "0.01"
os.environ["AUTH_SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app, reset_analytics_db_for_tests  # noqa: E402

TEST_AUTH_SECRET = "test-secret"
TEST_AUTH_ALGORITHM = "HS256"
client = TestClient(app)


def auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    reset_analytics_db_for_tests()


def test_trigger_and_complete_job():
    user_id = "analytics-user@example.com"
    response = client.post(
        "/jobs",
        headers=auth_headers(user_id),
        json={"job_type": "run_etl_transactions"},
    )
    assert response.status_code == 202
    payload = response.json()
    job_id = payload["job_id"]
    assert uuid.UUID(job_id)
    assert payload["user_id"] == user_id

    latest = payload
    for _ in range(30):
        poll = client.get(f"/jobs/{job_id}", headers=auth_headers(user_id))
        assert poll.status_code == 200
        latest = poll.json()
        if latest["status"] == "completed":
            break
        time.sleep(0.01)

    assert latest["status"] == "completed"
    assert latest["result"]["rows_processed"] == 15000


def test_job_scope_is_isolated_by_user():
    owner = "owner@example.com"
    other = "other@example.com"
    create = client.post(
        "/jobs",
        headers=auth_headers(owner),
        json={"job_type": "train_categorization_model"},
    )
    job_id = create.json()["job_id"]

    forbidden = client.get(f"/jobs/{job_id}", headers=auth_headers(other))
    assert forbidden.status_code == 404
