"""Tests for MTD Agent service."""

import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-mtd-agent")
os.environ.setdefault("OPENAI_API_KEY", "test-key")


# ── MTDAgent unit tests ──────────────────────────────────────────────────────

from app.mtd_agent import MTDAgent, MTDAgentResponse


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.hgetall = AsyncMock(return_value={
        "income":            "62000.0",
        "expenses":          "12000.0",
        "transaction_count": "80",
        "status":            "accumulating",
        "updated_at":        "2026-05-01T10:00:00+00:00",
    })
    r.aclose = AsyncMock()
    return r


@pytest.mark.asyncio
async def test_get_mtd_status_required(mock_redis):
    agent = MTDAgent(mock_redis, openai_api_key="")
    result = await agent.get_mtd_status("user1")

    assert isinstance(result, MTDAgentResponse)
    assert result.income == 62_000.0
    assert result.expenses == 12_000.0
    assert result.net_profit == 50_000.0
    assert result.mtd_required is True
    assert result.action_required is True
    assert len(result.actions) > 0


@pytest.mark.asyncio
async def test_get_mtd_status_not_required(mock_redis):
    mock_redis.hgetall = AsyncMock(return_value={
        "income":   "30000.0",
        "expenses": "5000.0",
        "status":   "accumulating",
    })
    agent = MTDAgent(mock_redis, openai_api_key="")
    result = await agent.get_mtd_status("user2")

    assert result.mtd_required is False
    assert result.income == 30_000.0


@pytest.mark.asyncio
async def test_template_explanation_no_api_key(mock_redis):
    agent = MTDAgent(mock_redis, openai_api_key="")
    result = await agent.get_mtd_status("user1")

    # Template fallback should produce a non-empty string
    assert len(result.message) > 10
    assert "MTD" in result.message


@pytest.mark.asyncio
async def test_answer_question_no_openai(mock_redis):
    agent = MTDAgent(mock_redis, openai_api_key="")
    answer = await agent.answer_question("user1", "When is my next MTD deadline?")
    # Without OpenAI, returns the prompt back
    assert isinstance(answer, str)
    assert len(answer) > 0


@pytest.mark.asyncio
async def test_determine_actions_urgent():
    r = AsyncMock()
    r.hgetall = AsyncMock(return_value={
        "income": "55000.0", "expenses": "5000.0", "status": "accumulating"
    })
    agent = MTDAgent(r, openai_api_key="")
    actions = agent._determine_actions(
        income=55_000.0, mtd_required=True, days_left=0, status="accumulating"
    )
    assert any("URGENT" in a for a in actions)


@pytest.mark.asyncio
async def test_determine_actions_approaching_threshold():
    r = AsyncMock()
    agent = MTDAgent(r, openai_api_key="")
    actions = agent._determine_actions(
        income=45_000.0, mtd_required=False, days_left=60, status="accumulating"
    )
    assert any("threshold" in a.lower() for a in actions)


def test_to_dict_contains_all_fields():
    resp = MTDAgentResponse(
        message="test", quarter="Q1 2026/27", income=10000.0,
        expenses=2000.0, net_profit=8000.0, mtd_required=False,
        days_until_deadline=90, submission_deadline="2026-08-05",
        action_required=False, actions=[],
    )
    d = resp.to_dict()
    for key in ["message", "quarter", "income", "expenses", "net_profit",
                "mtd_required", "days_until_deadline", "submission_deadline",
                "action_required", "actions"]:
        assert key in d


# ── FastAPI smoke tests ──────────────────────────────────────────────────────

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    with (
        patch("app.main.create_redis_client", new_callable=AsyncMock) as mock_rf,
        patch("app.main.MTDAgent") as mock_agent_cls,
    ):
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_rf.return_value = mock_redis

        mock_agent = AsyncMock()
        mock_agent.get_mtd_status = AsyncMock(return_value=MTDAgentResponse(
            message="You are on track.",
            quarter="Q1 2026/27",
            income=30000.0,
            expenses=5000.0,
            net_profit=25000.0,
            mtd_required=False,
            days_until_deadline=60,
            submission_deadline="2026-08-05",
            action_required=False,
            actions=[],
        ))
        mock_agent.answer_question = AsyncMock(return_value="Your deadline is 5 August.")
        mock_agent_cls.return_value = mock_agent

        from app.main import app as fastapi_app
        with TestClient(fastapi_app, raise_server_exceptions=False) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "mtd-agent"


def test_status_endpoint(client):
    r = client.get("/status/user123")
    assert r.status_code == 200


def test_question_endpoint(client):
    r = client.post("/question/user123", json={"question": "When is my deadline?"})
    assert r.status_code == 200
    assert "answer" in r.json()


def test_hmrc_callback_persists_token_in_redis(client):
    import app.main as mtd_main

    with patch.object(
        mtd_main.hmrc_client,
        "exchange_authorization_code",
        new_callable=AsyncMock,
    ) as ex:
        ex.return_value = ("hmrc-access-token", 3600)
        r = client.get("/hmrc/callback?code=auth-code-1&state=user-xyz")
    assert r.status_code == 200
    assert r.json().get("status") == "authorised"
    mtd_main.redis_client.set.assert_awaited_once()
    ca = mtd_main.redis_client.set.await_args
    assert ca.args[1] == "hmrc-access-token"
    assert ca.kwargs.get("ex") is not None


def test_submit_uses_token_from_redis(client):
    import app.main as mtd_main

    mtd_main.redis_client.get = AsyncMock(return_value="redis-stored-token")
    body = {
        "nino": "AB123456C",
        "tax_year": "2026-27",
        "period_start": "2026-04-06",
        "period_end": "2026-07-05",
        "income": 1000.0,
        "expenses": 100.0,
    }
    with patch.object(
        mtd_main.hmrc_client,
        "submit_period_summary",
        new_callable=AsyncMock,
    ) as sub:
        sub.return_value = {"transactionReference": "ref-1"}
        r = client.post("/submit/user-xyz", json=body)
    assert r.status_code == 200
    sub.assert_awaited_once()
    call_kw = sub.await_args.kwargs
    assert call_kw.get("access_token") == "redis-stored-token"


def test_health_returns_x_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")
