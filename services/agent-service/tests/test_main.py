import os
import sys

import pytest
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main as agent_main

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"


def _auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    async def fake_docs(_bearer_token: str, limit: int = 25) -> dict:
        return {
            "total": 2,
            "items": [
                {"id": "doc-1", "filename": "receipt-a.pdf"},
                {"id": "doc-2", "filename": "receipt-b.pdf"},
            ],
        }

    async def fake_unmatched(_bearer_token: str, limit: int = 15) -> dict:
        return {
            "total": 1,
            "items": [
                {
                    "draft_transaction": {"id": "draft-1", "filename": "receipt-a.pdf"},
                    "candidates": [{"transaction_id": "tx-22"}],
                }
            ],
        }

    async def fake_transactions(_bearer_token: str) -> list[dict]:
        return [
            {"id": "tx-1", "amount": 120.0},
            {"id": "tx-2", "amount": -40.0},
        ]

    async def fake_tax_snapshot(_bearer_token: str) -> dict:
        return {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "calculation": {
                "estimated_tax_due": 456.78,
                "total_income": 10000.0,
                "total_expenses": 2000.0,
            },
        }

    async def fake_execute_write_action(
        *,
        action_id: str,
        bearer_token: str,
        action_payload: dict,
    ) -> tuple[str, int, dict]:
        _ = bearer_token
        return f"/fake/{action_id}", 200, {"ok": True, "action_payload": action_payload}

    monkeypatch.setattr(agent_main, "_fetch_documents_review_queue", fake_docs)
    monkeypatch.setattr(agent_main, "_fetch_unmatched_receipt_drafts", fake_unmatched)
    monkeypatch.setattr(agent_main, "_fetch_transactions_me", fake_transactions)
    monkeypatch.setattr(agent_main, "_fetch_tax_snapshot", fake_tax_snapshot)
    monkeypatch.setattr(agent_main, "_execute_write_action", fake_execute_write_action)
    monkeypatch.setattr(agent_main, "_get_redis_client", lambda: None)
    monkeypatch.setattr(agent_main, "_in_memory_session_store", {})
    monkeypatch.setattr(agent_main, "_in_memory_confirmation_store", {})

    with TestClient(agent_main.app) as test_client:
        yield test_client


def test_agent_chat_requires_auth(client: TestClient):
    response = client.post("/agent/chat", json={"message": "Need readiness help"})
    assert response.status_code == 401


def test_agent_chat_routes_ocr_intent(client: TestClient):
    response = client.post(
        "/agent/chat",
        headers=_auth_headers("alice@example.com"),
        json={"message": "Please help with OCR review queue"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "ocr_review_assist"
    assert payload["answer"]
    assert len(payload["evidence"]) > 0
    assert payload["evidence"][0]["source_service"] == "documents-service"
    assert len(payload["suggested_actions"]) > 0


def test_agent_chat_routes_reconciliation_intent(client: TestClient):
    response = client.post(
        "/agent/chat",
        headers=_auth_headers("alice@example.com"),
        json={"message": "Need reconcile and match duplicate drafts"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "reconciliation_assist"
    assert any(item["source_endpoint"] == "/transactions/receipt-drafts/unmatched" for item in payload["evidence"])


def test_agent_chat_routes_tax_intent(client: TestClient):
    response = client.post(
        "/agent/chat",
        headers=_auth_headers("alice@example.com"),
        json={"message": "Prepare tax submission to HMRC"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "tax_pre_submit"
    assert any(item["source_service"] == "tax-engine" for item in payload["evidence"])
    assert len(payload["suggested_actions"]) >= 2


def test_agent_chat_defaults_to_readiness_snapshot(client: TestClient):
    response = client.post(
        "/agent/chat",
        headers=_auth_headers("alice@example.com"),
        json={"message": "What should I do next?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "readiness_check"
    assert len(payload["evidence"]) >= 3
    assert payload["answer"].startswith("Readiness snapshot:")


def test_agent_chat_persists_memory_for_same_session(client: TestClient):
    headers = _auth_headers("alice@example.com")
    first_response = client.post(
        "/agent/chat",
        headers=headers,
        json={"message": "Please help with OCR review queue", "session_id": "session-123"},
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["intent"] == "ocr_review_assist"
    assert first_payload["session_turn_count"] == 1

    second_response = client.post(
        "/agent/chat",
        headers=headers,
        json={"message": "continue", "session_id": "session-123"},
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["intent"] == "ocr_review_assist"
    assert second_payload["last_intent_from_memory"] == "ocr_review_assist"
    assert second_payload["session_turn_count"] == 2


def test_confirmation_token_flow_validates_and_consumes(client: TestClient):
    headers = _auth_headers("alice@example.com")
    request_payload = {
        "session_id": "session-456",
        "action_id": "tax.calculate_and_submit",
        "action_payload": {"jurisdiction": "UK", "start_date": "2025-01-01"},
    }
    token_response = client.post(
        "/agent/actions/request-confirmation",
        headers=headers,
        json=request_payload,
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()
    confirmation_token = token_payload["confirmation_token"]

    validate_response = client.post(
        "/agent/actions/validate-confirmation",
        headers=headers,
        json={
            "session_id": "session-456",
            "action_id": "tax.calculate_and_submit",
            "confirmation_token": confirmation_token,
            "action_payload": {"jurisdiction": "UK", "start_date": "2025-01-01"},
            "consume": True,
        },
    )
    assert validate_response.status_code == 200
    validate_payload = validate_response.json()
    assert validate_payload["valid"] is True
    assert validate_payload["consumed"] is True

    replay_response = client.post(
        "/agent/actions/validate-confirmation",
        headers=headers,
        json={
            "session_id": "session-456",
            "action_id": "tax.calculate_and_submit",
            "confirmation_token": confirmation_token,
            "action_payload": {"jurisdiction": "UK", "start_date": "2025-01-01"},
            "consume": True,
        },
    )
    assert replay_response.status_code == 200
    replay_payload = replay_response.json()
    assert replay_payload["valid"] is False
    assert replay_payload["reason"] == "token_already_used"


def test_confirmation_token_validation_rejects_payload_mismatch(client: TestClient):
    headers = _auth_headers("alice@example.com")
    token_response = client.post(
        "/agent/actions/request-confirmation",
        headers=headers,
        json={
            "session_id": "session-789",
            "action_id": "documents.review_document",
            "action_payload": {"document_id": "doc-1", "review_status": "confirmed"},
        },
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()

    mismatch_response = client.post(
        "/agent/actions/validate-confirmation",
        headers=headers,
        json={
            "session_id": "session-789",
            "action_id": "documents.review_document",
            "confirmation_token": token_payload["confirmation_token"],
            "action_payload": {"document_id": "doc-1", "review_status": "ignored"},
            "consume": False,
        },
    )
    assert mismatch_response.status_code == 200
    mismatch_payload = mismatch_response.json()
    assert mismatch_payload["valid"] is False
    assert mismatch_payload["reason"] == "payload_mismatch"


def test_confirmation_token_request_rejects_unsupported_action(client: TestClient):
    headers = _auth_headers("alice@example.com")
    response = client.post(
        "/agent/actions/request-confirmation",
        headers=headers,
        json={
            "session_id": "session-unsupported",
            "action_id": "unknown.action",
            "action_payload": {},
        },
    )
    assert response.status_code == 400


def test_execute_confirmed_action_success(client: TestClient):
    headers = _auth_headers("alice@example.com")
    request_payload = {
        "session_id": "session-exec",
        "action_id": "transactions.ignore_receipt_draft",
        "action_payload": {"draft_transaction_id": "draft-1"},
    }
    token_response = client.post(
        "/agent/actions/request-confirmation",
        headers=headers,
        json=request_payload,
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()

    execute_response = client.post(
        "/agent/actions/execute",
        headers=headers,
        json={
            "session_id": "session-exec",
            "action_id": "transactions.ignore_receipt_draft",
            "confirmation_token": token_payload["confirmation_token"],
            "action_payload": {"draft_transaction_id": "draft-1"},
        },
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["executed"] is True
    assert execute_payload["valid_confirmation"] is True
    assert execute_payload["downstream_status_code"] == 200


def test_execute_confirmed_action_rejects_invalid_confirmation(client: TestClient):
    headers = _auth_headers("alice@example.com")
    execute_response = client.post(
        "/agent/actions/execute",
        headers=headers,
        json={
            "session_id": "session-invalid",
            "action_id": "transactions.ignore_receipt_draft",
            "confirmation_token": "invalid-token",
            "action_payload": {"draft_transaction_id": "draft-1"},
        },
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["executed"] is False
    assert execute_payload["valid_confirmation"] is False
    assert execute_payload["confirmation_reason"] == "token_not_found_or_expired"


def test_execute_confirmed_action_rejects_replay(client: TestClient):
    headers = _auth_headers("alice@example.com")
    token_response = client.post(
        "/agent/actions/request-confirmation",
        headers=headers,
        json={
            "session_id": "session-replay",
            "action_id": "tax.calculate_and_submit",
            "action_payload": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "jurisdiction": "UK",
            },
        },
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()
    token = token_payload["confirmation_token"]

    first_execute = client.post(
        "/agent/actions/execute",
        headers=headers,
        json={
            "session_id": "session-replay",
            "action_id": "tax.calculate_and_submit",
            "confirmation_token": token,
            "action_payload": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "jurisdiction": "UK",
            },
        },
    )
    assert first_execute.status_code == 200
    assert first_execute.json()["executed"] is True

    second_execute = client.post(
        "/agent/actions/execute",
        headers=headers,
        json={
            "session_id": "session-replay",
            "action_id": "tax.calculate_and_submit",
            "confirmation_token": token,
            "action_payload": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "jurisdiction": "UK",
            },
        },
    )
    assert second_execute.status_code == 200
    second_payload = second_execute.json()
    assert second_payload["executed"] is False
    assert second_payload["confirmation_reason"] == "token_already_used"
