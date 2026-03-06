"""Shared Redis async client factory for mtd-agent."""
import os

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


async def create_redis_client() -> aioredis.Redis:
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
