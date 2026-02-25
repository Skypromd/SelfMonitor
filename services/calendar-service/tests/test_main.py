import os
import sys
import uuid

from fastapi.testclient import TestClient
from jose import jwt

TEST_DB_PATH = "/tmp/calendar_service_test.db"
os.environ["CALENDAR_DB_PATH"] = TEST_DB_PATH
os.environ["AUTH_SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app, reset_calendar_db_for_tests  # noqa: E402

TEST_AUTH_SECRET = "test-secret"
TEST_AUTH_ALGORITHM = "HS256"
client = TestClient(app)


def auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    reset_calendar_db_for_tests()


def test_create_and_list_user_events():
    user_id = "calendar-user@example.com"
    create_response = client.post(
        "/events",
        headers=auth_headers(user_id),
        json={
            "user_id": user_id,
            "event_title": "Tax deadline",
            "event_date": "2026-01-31",
            "notes": "Pay estimated self-assessment tax",
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert uuid.UUID(payload["id"])
    assert payload["user_id"] == user_id

    list_response = client.get("/events", headers=auth_headers(user_id))
    assert list_response.status_code == 200
    events = list_response.json()
    assert len(events) == 1
    assert events[0]["event_title"] == "Tax deadline"


def test_create_event_for_other_user_forbidden():
    response = client.post(
        "/events",
        headers=auth_headers("user-a@example.com"),
        json={
            "user_id": "user-b@example.com",
            "event_title": "Invalid scope",
            "event_date": "2026-01-31",
            "notes": None,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden user scope"
