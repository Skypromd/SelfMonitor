from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from .sources import GOVUK_WATCH_SOURCES

logger = logging.getLogger(__name__)

CONTENT_API_BASE = "https://www.gov.uk/api/content"


@dataclass(frozen=True)
class GovUkPageMeta:
    path: str
    public_updated_at: str | None
    first_published_at: str | None
    title: str | None
    schema_name: str | None
    base_path: str | None


async def fetch_page_meta(client: httpx.AsyncClient, path: str) -> GovUkPageMeta | None:
    url = f"{CONTENT_API_BASE}{path}"
    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 404:
            logger.warning("GOV.UK Content API 404 for %s", path)
            return None
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("GOV.UK Content API failed for %s: %s", path, exc)
        return None

    details = data.get("details") or {}
    return GovUkPageMeta(
        path=path,
        public_updated_at=details.get("public_updated_at"),
        first_published_at=details.get("first_public_at"),
        title=details.get("title"),
        schema_name=data.get("schema_name"),
        base_path=data.get("base_path"),
    )


def _newer_than(prev: str | None, current: str | None) -> bool:
    if not current:
        return False
    if not prev:
        return True
    return current != prev


async def check_govuk_sources_for_updates(
    client: httpx.AsyncClient,
    last_known: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Compare Content API public_updated_at to last_known[state_key].
    Returns (events_for_changelog, merged_state).
    """
    merged = dict(last_known)
    events: list[dict[str, Any]] = []

    metas = await asyncio.gather(
        *[fetch_page_meta(client, src["path"]) for src in GOVUK_WATCH_SOURCES],
    )

    for src, meta in zip(GOVUK_WATCH_SOURCES, metas, strict=True):
        if meta is None:
            merged[src["id"]] = {
                "path": src["path"],
                "label": src["label"],
                "last_error": True,
            }
            continue

        key = src["id"]
        prev = None
        if isinstance(merged.get(key), dict):
            prev = merged[key].get("public_updated_at")

        current = meta.public_updated_at
        entry = {
            "path": src["path"],
            "label": src["label"],
            "title": meta.title,
            "public_updated_at": current,
            "first_published_at": meta.first_published_at,
            "schema_name": meta.schema_name,
            "base_path": meta.base_path,
            "last_error": False,
        }
        merged[key] = entry

        if _newer_than(prev, current):
            events.append(
                {
                    "source_id": key,
                    "path": src["path"],
                    "label": src["label"],
                    "title": meta.title,
                    "previous_public_updated_at": prev,
                    "public_updated_at": current,
                }
            )

    return events, merged
