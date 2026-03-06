"""
FinOps context reader for SelfMate.

Reads pre-computed context keys written by the finops-monitor service, so
SelfMate no longer needs to call 35 microservices directly on every chat turn.

Redis keys consumed (written by finops-monitor):
  finops:balance:{user_id}              – latest balance (hgetall)
  mtd:quarterly:{user_id}:{ty}:{q}      – current quarter MTD totals (hgetall)
  finops:alerts (stream)                – recent unread alerts for the user
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


def _current_quarter_key(user_id: str) -> str:
    """Compute the Redis key for the user's current MTD quarter."""
    today = date.today()
    if today.month > 4 or (today.month == 4 and today.day >= 6):
        year = today.year
    else:
        year = today.year - 1

    m = today.month
    if (m == 4 and today.day >= 6) or 5 <= m <= 7:
        q = "Q1"
    elif 7 <= m <= 10:
        q = "Q2"
    elif m >= 10 or m <= 1:
        q = "Q3"
    else:
        q = "Q4"

    ty = f"{year}-{str(year + 1)[-2:]}"
    return f"mtd:quarterly:{user_id}:{ty}:{q}"


async def get_finops_context(redis_client: Any, user_id: str) -> dict:
    """
    Return a merged financial context dict for *user_id* from FinOps Monitor Redis cache.

    Falls back gracefully on any Redis error (returns empty sub-dicts).
    """
    try:
        balance_raw  = await redis_client.hgetall(f"finops:balance:{user_id}") or {}
        mtd_raw      = await redis_client.hgetall(_current_quarter_key(user_id)) or {}
    except Exception as exc:
        log.warning("FinOps Redis read failed for %s: %s", user_id, exc)
        balance_raw = {}
        mtd_raw     = {}

    income   = float(mtd_raw.get("income",   0))
    expenses = float(mtd_raw.get("expenses", 0))

    return {
        "source":           "finops-monitor",
        "balance":          float(balance_raw.get("available_balance", 0)),
        "currency":         balance_raw.get("currency", "GBP"),
        "balance_updated":  balance_raw.get("updated_at"),
        "mtd": {
            "quarter":       mtd_raw.get("quarter",  ""),
            "income":        income,
            "expenses":      expenses,
            "net_profit":    round(income - expenses, 2),
            "tx_count":      int(mtd_raw.get("transaction_count", 0)),
            "status":        mtd_raw.get("status", "accumulating"),
            "mtd_required":  income >= 50_000.0,
            "updated_at":    mtd_raw.get("updated_at"),
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
