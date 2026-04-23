import os
import sys

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app  # noqa: E402

client = TestClient(app)
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"


def _headers() -> dict[str, str]:
    token = jwt.encode({"sub": "u1@example.com"}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def test_list_calculations_bad_tax_year():
    r = client.get(
        "/integrations/hmrc/self-assessment/2024-250/calculations",
        params={"nino": "AA123456A"},
        headers=_headers(),
    )
    assert r.status_code == 400


def test_list_calculations_bad_nino():
    r = client.get(
        "/integrations/hmrc/self-assessment/2024-25/calculations",
        params={"nino": "SHORT"},
        headers=_headers(),
    )
    assert r.status_code == 400


def test_list_calculations_returns_simulated_payload():
    r = client.get(
        "/integrations/hmrc/self-assessment/2024-25/calculations",
        params={"nino": "AA 123456 A"},
        headers=_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("mode") == "simulated"
    assert data.get("tax_year") == "2024-25"
    assert data.get("nino") == "AA123456A"
    assert isinstance(data.get("calculations"), list)


def test_trigger_calculation_returns_payload():
    r = client.post(
        "/integrations/hmrc/self-assessment/2024-25/calculations/trigger",
        params={"nino": "AA123456A"},
        headers=_headers(),
        json={"calculation_type": "in-year"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("mode") == "simulated"
    assert "calculationId" in data


def test_retrieve_calculation_returns_payload():
    r = client.get(
        "/integrations/hmrc/self-assessment/2024-25/calculations/calc-test-id",
        params={"nino": "AA123456A"},
        headers=_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("mode") == "simulated"
    assert data.get("calculationId") == "calc-test-id"


def test_list_with_direct_mode_uses_hmrc(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "HMRC_DIRECT_SUBMISSION_ENABLED", True)
    monkeypatch.setattr(main, "HMRC_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr(main, "HMRC_OAUTH_CLIENT_SECRET", "sec")

    async def fake_token(**kwargs):
        return "tok"

    class FakeResp:
        status_code = 200
        content = b"{}"
        text = ""

        def json(self):
            return {"items": [{"calculationId": "abc"}]}

    async def fake_hmrc_request(*args, **kwargs):
        return FakeResp()

    monkeypatch.setattr("app.hmrc_individual_calculations._fetch_hmrc_oauth_access_token", fake_token)
    monkeypatch.setattr("app.hmrc_individual_calculations._hmrc_json_request", fake_hmrc_request)

    r = client.get(
        "/integrations/hmrc/self-assessment/2024-25/calculations",
        params={"nino": "AA123456A"},
        headers=_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("mode") == "hmrc"
    assert body.get("nino") == "AA123456A"
