import os
import sys

from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app  # noqa: E402

TEST_AUTH_SECRET = "a_very_secret_key_that_should_be_in_an_env_var"
TEST_AUTH_ALGORITHM = "HS256"
client = TestClient(app)


def auth_headers(user_id: str = "categorization-user@example.com") -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, TEST_AUTH_SECRET, algorithm=TEST_AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_rule_based_categorization():
    response = client.post(
        "/categorize",
        headers=auth_headers(),
        json={"description": "Tesco groceries order"},
    )
    assert response.status_code == 200
    assert response.json()["category"] == "groceries"


def test_categorization_requires_auth():
    response = client.post("/categorize", json={"description": "Salary payment"})
    assert response.status_code == 401
