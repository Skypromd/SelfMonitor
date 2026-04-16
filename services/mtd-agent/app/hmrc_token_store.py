"""HMRC user authorization-code access tokens in Redis (survives process restarts)."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

KEY_PREFIX = "mtd:hmrc:oauth:access"


def _key(user_id: str) -> str:
    return f"{KEY_PREFIX}:{user_id}"


async def store_hmrc_user_access_token(
    redis: Any,
    user_id: str,
    access_token: str,
    expires_in: int | None,
) -> None:
    base = int(expires_in) if expires_in is not None else 3600
    ex = max(60, base - 60)
    await redis.set(_key(user_id), access_token, ex=ex)
    log.info("Stored HMRC OAuth access token for user %s (ttl ~%ss)", user_id, ex)


async def get_hmrc_user_access_token(redis: Any, user_id: str) -> str | None:
    token = await redis.get(_key(user_id))
    if token is None:
        return None
    return str(token)
