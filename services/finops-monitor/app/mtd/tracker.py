"""
MTD quarterly income/expense accumulator.

For every user we maintain a Redis hash:
    Key:  mtd:quarterly:{user_id}:{tax_year}:{quarter_num}
    Fields:
        income         – running total (float, £)
        expenses       – running total (float, £)
        transaction_count
        updated_at     – ISO timestamp of last update
        status         – "accumulating" | "ready" | "submitted"

MTD threshold for 2026/27: £50,000 turnover.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.mtd.deadlines import MTDQuarter, get_current_quarter, is_mtd_required

_REDIS_KEY_PREFIX = "mtd:quarterly"
_TURNOVER_THRESHOLD = 50_000.0


# ── data classes ─────────────────────────────────────────────────────────────

class QuarterlyAccumulator:
    """Reads/writes a single user-quarter record via a Redis client."""

    def __init__(self, redis_client: Any, user_id: str) -> None:
        self._redis = redis_client
        self.user_id = user_id

    # ── key helpers ──────────────────────────────────────────────────────────

    def _key(self, quarter: MTDQuarter) -> str:
        safe_year = quarter.tax_year.replace("/", "-")
        q_num = quarter.label.split()[0]          # "Q1", "Q2", etc.
        return f"{_REDIS_KEY_PREFIX}:{self.user_id}:{safe_year}:{q_num}"

    # ── read ─────────────────────────────────────────────────────────────────

    async def get(self, quarter: MTDQuarter | None = None) -> dict:
        """Return current accumulator data for *quarter* (default: current quarter)."""
        q = quarter or get_current_quarter()
        raw = await self._redis.hgetall(self._key(q))
        if not raw:
            return {
                "user_id": self.user_id,
                "quarter": q.label,
                "tax_year": q.tax_year,
                "period_start": q.start.isoformat(),
                "period_end": q.end.isoformat(),
                "submission_deadline": q.submission_deadline.isoformat(),
                "income": 0.0,
                "expenses": 0.0,
                "net_profit": 0.0,
                "transaction_count": 0,
                "status": "accumulating",
                "updated_at": None,
                "mtd_required": False,
            }
        income   = float(raw.get("income", 0))
        expenses = float(raw.get("expenses", 0))
        return {
            "user_id": self.user_id,
            "quarter": q.label,
            "tax_year": q.tax_year,
            "period_start": q.start.isoformat(),
            "period_end": q.end.isoformat(),
            "submission_deadline": q.submission_deadline.isoformat(),
            "income": income,
            "expenses": expenses,
            "net_profit": round(income - expenses, 2),
            "transaction_count": int(raw.get("transaction_count", 0)),
            "status": raw.get("status", "accumulating"),
            "updated_at": raw.get("updated_at"),
            "mtd_required": is_mtd_required(income),
        }

    async def get_all_quarters(self, tax_year: str) -> list[dict]:
        """Return data for all 4 quarters in the given tax year."""
        from app.mtd.deadlines import _quarters_for_tax_year
        year_start = int(tax_year.split("/")[0])
        quarters = _quarters_for_tax_year(year_start)
        results = []
        for q in quarters:
            results.append(await self.get(q))
        return results

    # ── write ────────────────────────────────────────────────────────────────

    async def add_transaction(
        self,
        amount: float,
        transaction_type: str,             # "income" | "expense"
        quarter: MTDQuarter | None = None,
    ) -> dict:
        """Increment running totals with a single transaction."""
        q = quarter or get_current_quarter()
        key = self._key(q)
        now_iso = datetime.now(timezone.utc).isoformat()

        if transaction_type == "income":
            await self._redis.hincrbyfloat(key, "income", amount)
        elif transaction_type == "expense":
            await self._redis.hincrbyfloat(key, "expenses", amount)

        await self._redis.hincrby(key, "transaction_count", 1)
        await self._redis.hset(key, "updated_at", now_iso)
        # Ensure status is initialised
        await self._redis.hsetnx(key, "status", "accumulating")

        return await self.get(q)

    async def bulk_sync(
        self,
        income: float,
        expenses: float,
        transaction_count: int,
        quarter: MTDQuarter | None = None,
    ) -> dict:
        """Overwrite totals with pre-aggregated values (e.g. from daily sync job)."""
        q = quarter or get_current_quarter()
        key = self._key(q)
        now_iso = datetime.now(timezone.utc).isoformat()

        await self._redis.hset(key, mapping={
            "income":            income,
            "expenses":          expenses,
            "transaction_count": transaction_count,
            "updated_at":        now_iso,
        })
        await self._redis.hsetnx(key, "status", "accumulating")
        return await self.get(q)

    async def mark_submitted(self, quarter: MTDQuarter | None = None) -> None:
        """Mark a quarter as submitted to HMRC."""
        q = quarter or get_current_quarter()
        await self._redis.hset(self._key(q), "status", "submitted")

    async def mark_ready(self, quarter: MTDQuarter | None = None) -> None:
        """Mark a quarter as ready for submission."""
        q = quarter or get_current_quarter()
        await self._redis.hset(self._key(q), "status", "ready")


# ── standalone helper (no Redis) ─────────────────────────────────────────────

def calculate_quarterly_summary(transactions: list[dict]) -> dict:
    """
    Pure-Python aggregation over a list of transaction dicts.

    Each dict must have:
      - amount (float, positive)
      - transaction_type ("income" | "expense")
      - date (ISO string or datetime.date)
    """
    income   = sum(t["amount"] for t in transactions if t["transaction_type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["transaction_type"] == "expense")
    return {
        "income":            round(income, 2),
        "expenses":          round(expenses, 2),
        "net_profit":        round(income - expenses, 2),
        "transaction_count": len(transactions),
        "mtd_required":      is_mtd_required(income),
    }
