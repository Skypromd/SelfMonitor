import os
import sys
import tempfile

os.environ["AUTH_SECRET_KEY"] = "test-secret"
_learn_fd, _learn_path = tempfile.mkstemp(suffix=".json")
os.close(_learn_fd)
os.environ["CATEGORIZATION_LEARNED_RULES_PATH"] = _learn_path

from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app  # noqa: E402

TEST_AUTH_SECRET = "test-secret"
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


def test_learn_invalid_category():
    response = client.post(
        "/learn",
        headers=auth_headers(),
        json={"description": "Some shop", "category": "not_a_real_category_slug"},
    )
    assert response.status_code == 422


def test_learn_then_categorize_prefers_user_rule():
    uid = "learn-test-user@example.com"
    learn = client.post(
        "/learn",
        headers=auth_headers(uid),
        json={"description": "ZZLEARNEXOTIC MART LONDON", "category": "transport"},
    )
    assert learn.status_code == 200
    assert learn.json()["stored"] is True
    cat = client.post(
        "/categorize",
        headers=auth_headers(uid),
        json={"description": "VISA ZZLEARNEXOTIC MART LONDON GB REF 12"},
    )
    assert cat.status_code == 200
    assert cat.json()["category"] == "transport"


def test_bulk_categorize_uses_learned_rule():
    uid = "bulk-learn-user@example.com"
    client.post(
        "/learn",
        headers=auth_headers(uid),
        json={"description": "ZZBULKCOFFEE SHOP", "category": "food_and_drink"},
    )
    bulk = client.post(
        "/categorize/bulk",
        headers=auth_headers(uid),
        json={"descriptions": ["DEBIT ZZBULKCOFFEE SHOP 44"]},
    )
    assert bulk.status_code == 200
    rows = bulk.json()["results"]
    assert len(rows) == 1
    assert rows[0]["category"] == "food_and_drink"


def test_other_user_does_not_see_learned_rule():
    client.post(
        "/learn",
        headers=auth_headers("owner-a@example.com"),
        json={"description": "ZZPRIVATECHAIN STORE", "category": "software"},
    )
    cat = client.post(
        "/categorize",
        headers=auth_headers("owner-b@example.com"),
        json={"description": "PAYMENT ZZPRIVATECHAIN STORE"},
    )
    assert cat.status_code == 200
    assert cat.json()["category"] != "software"
