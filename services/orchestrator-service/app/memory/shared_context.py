"""
Shared Redis context — stores cross-agent user state.
All specialist agents can read/write here so they share awareness.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

REDIS_URL   = os.getenv("REDIS_URL", "redis://redis:6379/9")
TTL_SECONDS = int(os.getenv("CONTEXT_TTL_SECONDS", "3600"))

_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]
            _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        except Exception:
            return None
    return _redis_client


async def get_user_context(user_id: str) -> dict[str, Any]:
    r = await _get_redis()
    if not r:
        return {}
    try:
        raw = await r.get(f"orchestrator:ctx:{user_id}")
        return json.loads(raw) if raw else {}
    except Exception as exc:
        log.debug("Redis get failed: %s", exc)
        return {}


async def set_user_context(user_id: str, data: dict[str, Any]) -> None:
    r = await _get_redis()
    if not r:
        return
    try:
        existing = await get_user_context(user_id)
        merged = {**existing, **data}
        await r.setex(f"orchestrator:ctx:{user_id}", TTL_SECONDS, json.dumps(merged))
    except Exception as exc:
        log.debug("Redis set failed: %s", exc)


async def append_audit_log(user_id: str, entry: dict[str, Any]) -> None:
    r = await _get_redis()
    if not r:
        return
    try:
        key = f"orchestrator:audit:{user_id}"
        await r.lpush(key, json.dumps(entry))
        await r.ltrim(key, 0, 99)   # keep last 100 entries
        await r.expire(key, 86400 * 7)
    except Exception as exc:
        log.debug("Redis audit log failed: %s", exc)


async def get_audit_log(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    r = await _get_redis()
    if not r:
        return []
    try:
        raw_list = await r.lrange(f"orchestrator:audit:{user_id}", 0, limit - 1)
        return [json.loads(raw) for raw in raw_list]
    except Exception:
        return []
