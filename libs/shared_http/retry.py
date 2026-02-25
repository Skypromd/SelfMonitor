import asyncio
from typing import Any

import httpx


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


async def _retry_delay(attempt: int, base_delay_seconds: float) -> None:
    await asyncio.sleep(base_delay_seconds * (2 ** (attempt - 1)))


async def get_json_with_retry(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    attempts: int = 3,
    base_delay_seconds: float = 0.25,
) -> Any:
    async with httpx.AsyncClient() as client:
        for attempt in range(1, attempts + 1):
            try:
                response = await client.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt >= attempts or not _is_retryable_error(exc):
                    raise
                await _retry_delay(attempt, base_delay_seconds)


async def post_json_with_retry(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 10.0,
    attempts: int = 3,
    base_delay_seconds: float = 0.25,
    expect_json: bool = True,
) -> Any:
    async with httpx.AsyncClient() as client:
        for attempt in range(1, attempts + 1):
            try:
                response = await client.post(url, headers=headers, json=json_body, timeout=timeout)
                response.raise_for_status()
                if not expect_json or not response.content:
                    return None
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt >= attempts or not _is_retryable_error(exc):
                    raise
                await _retry_delay(attempt, base_delay_seconds)

