"""
Redis Streams pub/sub bus for the FinOps Monitor.

Streams
-------
  finops:events               – all monitoring events (debug/audit)
  finops:alerts               – urgent alerts (low balance, fraud, overdue invoices)
  finops:mtd:{user_id}        – MTD-specific events for a user

Event format
------------
Each event is a plain dict; fields are stored as individual stream fields
so that consumers can filter server-side with XREAD / XREADGROUP.

Helper
------
  publish_event(redis, stream, event)  – add event to stream, returns message ID
  read_events(redis, stream, ...)      – read new events from a stream
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis.asyncio as aioredis

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Maximum number of messages to keep in each stream (MAXLEN trim)
_STREAM_MAXLEN = 10_000


class EventType:
    """Shared event-type constants used across monitors and MTD module."""
    FRAUD_ALERT          = "fraud_alert"
    LOW_BALANCE          = "low_balance"
    INVOICE_OVERDUE      = "invoice_overdue"
    INVOICE_DUE_SOON     = "invoice_due_soon"
    MTD_THRESHOLD_BREACH = "mtd_threshold_breach"
    MTD_DEADLINE_WARNING = "mtd_deadline_warning"
    MTD_REPORT_READY     = "mtd_report_ready"
    MTD_SUBMITTED        = "mtd_submitted"


# ── connection factory ────────────────────────────────────────────────────────

async def create_redis_client() -> aioredis.Redis:
    """Create and return an async Redis client from REDIS_URL."""
    client = await aioredis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    return client


# ── publish / consume ─────────────────────────────────────────────────────────

async def publish_event(
    redis_client: Any,
    stream: str,
    event: dict,
) -> str:
    """
    Add *event* to a Redis stream.

    All dict values are serialised to strings so they can be stored as
    stream fields. Returns the generated message ID.
    """
    # Flatten nested dicts to JSON string so Redis can store them
    flat: dict[str, str] = {
        k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
        for k, v in event.items()
    }
    msg_id = await redis_client.xadd(stream, flat, maxlen=_STREAM_MAXLEN, approximate=True)
    log.debug("Published %s → %s (id=%s)", event.get("type"), stream, msg_id)
    return msg_id


async def read_events(
    redis_client: Any,
    stream: str,
    last_id: str = "$",
    count: int = 100,
    block_ms: int = 0,
) -> list[tuple[str, dict]]:
    """
    Read new messages from *stream* starting after *last_id*.

    Returns list of (message_id, fields_dict) tuples.
    Pass last_id=">" when using consumer groups; "$" for latest-only reads.
    """
    result = await redis_client.xread(
        {stream: last_id},
        count=count,
        block=block_ms or None,
    )
    if not result:
        return []

    # result = [(stream_name, [(id, fields), ...])]
    messages: list[tuple[str, dict]] = []
    for _stream_name, entries in result:
        for msg_id, fields in entries:
            messages.append((msg_id, fields))

    return messages


async def get_latest_context(redis_client: Any, user_id: str) -> dict:
    """
    Aggregate the most recent cached context for a user.
    Used by SelfMate to avoid calling all 35 services per request.
    """
    balance_raw = await redis_client.hgetall(f"finops:balance:{user_id}")

    # Latest MTD status (current quarter) — try each quarter key pattern
    import datetime as _dt
    today = _dt.date.today()
    from app.mtd.deadlines import get_current_quarter
    try:
        q = get_current_quarter(today)
        safe_year = q.tax_year.replace("/", "-")
        q_num = q.label.split()[0]
        mtd_raw = await redis_client.hgetall(
            f"mtd:quarterly:{user_id}:{safe_year}:{q_num}"
        )
    except Exception:
        mtd_raw = {}

    return {
        "balance":          balance_raw,
        "current_quarter":  mtd_raw,
    }
