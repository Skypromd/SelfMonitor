"""
Tests for finops-monitor service.

Run with:
    cd services/finops-monitor
    pip install -r requirements.txt
    python -m pytest -q tests/test_main.py
"""

import os
import sys
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Must be set before importing app.main
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-finops")

# ── MTD deadline tests ─────────────────────────────────────────────────────────

from app.mtd.deadlines import (
    MTDQuarter,
    _quarters_for_tax_year,
    days_until_deadline,
    get_current_quarter,
    get_next_deadline,
    is_mtd_required,
)


class TestMTDDeadlines:
    def test_quarters_for_2026(self):
        quarters = _quarters_for_tax_year(2026)
        assert len(quarters) == 4
        labels = [q.label for q in quarters]
        assert "Q1 2026/27" in labels
        assert "Q4 2026/27" in labels

    def test_q1_dates(self):
        q1 = _quarters_for_tax_year(2026)[0]
        assert q1.start  == date(2026, 4, 6)
        assert q1.end    == date(2026, 7, 5)
        assert q1.submission_deadline == date(2026, 8, 5)

    def test_q3_crosses_year(self):
        q3 = _quarters_for_tax_year(2026)[2]
        assert q3.start == date(2026, 10, 6)
        assert q3.end   == date(2027,  1,  5)
        assert q3.submission_deadline == date(2027, 2, 5)

    def test_q4_dates(self):
        q4 = _quarters_for_tax_year(2026)[3]
        assert q4.start == date(2027, 1, 6)
        assert q4.end   == date(2027, 4, 5)
        assert q4.submission_deadline == date(2027, 5, 5)

    def test_get_current_quarter_in_q1(self):
        q = get_current_quarter(reference=date(2026, 5, 1))
        assert q.label == "Q1 2026/27"

    def test_get_current_quarter_in_q2(self):
        q = get_current_quarter(reference=date(2026, 8, 1))
        assert q.label == "Q2 2026/27"

    def test_get_current_quarter_in_q3(self):
        q = get_current_quarter(reference=date(2026, 11, 1))
        assert q.label == "Q3 2026/27"

    def test_get_current_quarter_in_q4(self):
        q = get_current_quarter(reference=date(2027, 2, 1))
        assert q.label == "Q4 2026/27"

    def test_is_mtd_required_above_threshold(self):
        assert is_mtd_required(50_001) is True
        assert is_mtd_required(50_000) is True

    def test_is_mtd_required_below_threshold(self):
        assert is_mtd_required(49_999) is False


# ── MTD tracker tests ─────────────────────────────────────────────────────────

from app.mtd.tracker import QuarterlyAccumulator, calculate_quarterly_summary


class TestQuarterlyAccumulator:
    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.hgetall = AsyncMock(return_value={})
        r.hincrbyfloat = AsyncMock()
        r.hincrby = AsyncMock()
        r.hset = AsyncMock()
        r.hsetnx = AsyncMock()
        return r

    @pytest.mark.asyncio
    async def test_get_empty_returns_defaults(self, mock_redis):
        acc = QuarterlyAccumulator(mock_redis, "user1")
        data = await acc.get(get_current_quarter(reference=date(2026, 5, 1)))
        assert data["income"]   == 0.0
        assert data["expenses"] == 0.0
        assert data["status"]   == "accumulating"
        assert data["mtd_required"] is False

    @pytest.mark.asyncio
    async def test_get_with_redis_data(self, mock_redis):
        mock_redis.hgetall = AsyncMock(return_value={
            "income": "55000.0",
            "expenses": "10000.0",
            "transaction_count": "42",
            "status": "accumulating",
            "updated_at": "2026-06-01T10:00:00+00:00",
        })
        acc = QuarterlyAccumulator(mock_redis, "user1")
        data = await acc.get(get_current_quarter(reference=date(2026, 5, 1)))
        assert data["income"]       == 55_000.0
        assert data["net_profit"]   == 45_000.0
        assert data["mtd_required"] is True


def test_calculate_quarterly_summary():
    transactions = [
        {"amount": 10_000, "transaction_type": "income",  "date": "2026-05-01"},
        {"amount":  5_000, "transaction_type": "income",  "date": "2026-05-15"},
        {"amount":  2_000, "transaction_type": "expense", "date": "2026-05-10"},
    ]
    result = calculate_quarterly_summary(transactions)
    assert result["income"]   == 15_000
    assert result["expenses"] ==  2_000
    assert result["net_profit"] == 13_000
    assert result["transaction_count"] == 3
    assert result["mtd_required"] is False   # 15k < 50k


# ── report builder tests ──────────────────────────────────────────────────────

from app.mtd.report_builder import build_report, validate_report


class TestReportBuilder:
    def test_build_report_fields(self):
        r = build_report(
            user_id="u1",
            nino="AB123456C",
            utr="1234567890",
            quarter_label="Q1 2026/27",
            tax_year="2026/27",
            period_start="2026-04-06",
            period_end="2026-07-05",
            submission_deadline="2026-08-05",
            income_total=20_000.0,
            expenses_total=5_000.0,
        )
        assert r["net_profit"] == 15_000.0
        assert r["tax_year_hmrc"] == "2026-27"
        assert r["status"] == "draft"
        assert r["income"]["total"] == 20_000.0

    def test_validate_report_valid(self):
        r = build_report(
            user_id="u1", nino="AB123456C", utr="123",
            quarter_label="Q2 2026/27", tax_year="2026/27",
            period_start="2026-07-06", period_end="2026-10-05",
            submission_deadline="2026-11-05",
            income_total=1000.0, expenses_total=200.0,
        )
        assert validate_report(r) == []

    def test_validate_report_missing_nino(self):
        r = build_report(
            user_id="u1", nino="", utr="123",
            quarter_label="Q2 2026/27", tax_year="2026/27",
            period_start="2026-07-06", period_end="2026-10-05",
            submission_deadline="2026-11-05",
            income_total=1000.0, expenses_total=200.0,
        )
        errors = validate_report(r)
        assert any("nino" in e for e in errors)


# ── FastAPI endpoint smoke tests ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Create a TestClient with mocked Redis and scheduler."""
    import app.main  # ensure module is in sys.modules before patching  # noqa: F401
    with (
        patch("app.main.create_redis_client", new_callable=AsyncMock) as mock_redis_factory,
        patch("app.main.scheduler") as mock_scheduler,
    ):
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.aclose = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        mock_scheduler.running = False

        # Import here to pick up the patches
        from app.main import app as fastapi_app
        with TestClient(fastapi_app, raise_server_exceptions=False) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_status_endpoint(client):
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert "days_until_deadline" in body
    assert "next_deadline" in body
