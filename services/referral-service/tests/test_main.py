import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

from unittest.mock import AsyncMock, patch, MagicMock
import uuid
import datetime

import pytest
from jose import jwt
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH_SECRET_KEY = "test-secret"
AUTH_ALGORITHM = "HS256"


def make_token(sub: str = "test-user-123") -> str:
    return jwt.encode({"sub": sub}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


VALID_TOKEN = make_token()
AUTH_HEADER = {"Authorization": f"Bearer {VALID_TOKEN}"}


# --- Health check ---

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Auth required endpoints return 401 without token ---

def test_create_referral_code_no_auth():
    resp = client.post("/referral-codes")
    assert resp.status_code == 401


def test_validate_referral_no_auth():
    resp = client.post("/validate-referral", json={"code": "ABC"})
    assert resp.status_code == 401


def test_stats_no_auth():
    resp = client.get("/stats")
    assert resp.status_code == 401


def test_leaderboard_no_auth():
    resp = client.get("/leaderboard")
    assert resp.status_code == 401


def test_join_campaign_no_auth():
    resp = client.post("/campaigns/some-id/join")
    assert resp.status_code == 401


# --- Authenticated endpoints with mocked DB ---

@patch("app.main.crud.get_referral_code_by_user")
def test_create_referral_code_existing(mock_get):
    fake_code = MagicMock()
    fake_code.is_active = True
    fake_code.id = uuid.uuid4()
    fake_code.user_id = "test-user-123"
    fake_code.code = "ABCD1234"
    fake_code.campaign_type = "standard"
    fake_code.reward_amount = 25.0
    fake_code.max_uses = 50
    fake_code.created_at = datetime.datetime.now(datetime.UTC)
    fake_code.expires_at = None
    mock_get.return_value = fake_code

    resp = client.post("/referral-codes", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "ABCD1234"


@patch("app.main.crud.create_referral_code")
@patch("app.main.crud.get_referral_code_by_user")
def test_create_referral_code_new(mock_get, mock_create):
    mock_get.return_value = None
    new_code = MagicMock()
    new_code.id = uuid.uuid4()
    new_code.user_id = "test-user-123"
    new_code.code = "NEWCODE1"
    new_code.campaign_type = "standard"
    new_code.reward_amount = 25.0
    new_code.max_uses = 50
    new_code.is_active = True
    new_code.created_at = datetime.datetime.now(datetime.UTC)
    new_code.expires_at = None
    mock_create.return_value = new_code

    resp = client.post("/referral-codes", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["code"] == "NEWCODE1"


@patch("app.main.crud.get_referral_code_by_code")
def test_validate_referral_invalid_code(mock_get):
    mock_get.return_value = None
    resp = client.post("/validate-referral", json={"code": "INVALID"}, headers=AUTH_HEADER)
    assert resp.status_code == 404


@patch("app.main.crud.get_referral_code_by_user")
def test_get_stats_no_code(mock_get):
    mock_get.return_value = None
    resp = client.get("/stats", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_referrals"] == 0


@patch("app.main.crud.get_referral_statistics")
@patch("app.main.crud.get_referral_code_by_user")
def test_get_stats_with_code(mock_get_code, mock_stats):
    fake_code = MagicMock()
    fake_code.id = uuid.uuid4()
    mock_get_code.return_value = fake_code

    from app.schemas import ReferralStats
    mock_stats.return_value = ReferralStats(
        total_referrals=5,
        active_referrals=3,
        total_earned=125.0,
        pending_rewards=25.0,
        conversions_this_month=2,
    )

    resp = client.get("/stats", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_referrals"] == 5


@patch("app.main.crud.get_user_referral_rank")
@patch("app.main.crud.get_referral_leaderboard")
def test_get_leaderboard(mock_lb, mock_rank):
    mock_lb.return_value = [
        {"user_id": "u1", "code": "AAA", "referral_count": 10, "total_earned": 250.0}
    ]
    mock_rank.return_value = 5
    resp = client.get("/leaderboard", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    assert "leaderboard" in data
    assert data["your_position"] == 5


@patch("app.main.crud.get_campaign_by_id")
def test_join_campaign_not_found(mock_get):
    mock_get.return_value = None
    resp = client.post("/campaigns/some-id/join", headers=AUTH_HEADER)
    assert resp.status_code == 404
