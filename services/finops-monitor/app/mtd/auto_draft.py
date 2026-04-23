"""Background MTD quarterly draft persistence (roadmap 2.3) — no HMRC submit."""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from typing import Any

import httpx

log = logging.getLogger(__name__)

_QUARTER_LABEL_RE = re.compile(r"^(Q[1-4])\s+(\d{4})/(\d{2})\s*$")


def parse_quarter_label_for_tax_engine(label: str) -> tuple[int, str]:
    m = _QUARTER_LABEL_RE.match(label.strip())
    if not m:
        raise ValueError(f"unrecognised quarter label: {label!r}")
    return int(m.group(2)), m.group(1)


async def try_mtd_auto_draft_for_upcoming_deadline(
    redis: Any,
    *,
    user_id: str,
    next_q_label: str,
    deadline: date,
    days_before_deadline: int,
) -> None:
    if days_before_deadline != 3:
        return
    secret = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()
    tax_base = os.getenv("TAX_ENGINE_SERVICE_URL", "http://tax-engine:80").rstrip("/")
    if not secret:
        return
    try:
        tax_year_start_year, quarter = parse_quarter_label_for_tax_engine(next_q_label)
    except ValueError as exc:
        log.warning("auto-draft skip %s: %s", user_id, exc)
        return

    dedup_key = f"mtd:auto_draft_quarterly:{user_id}:{deadline.isoformat()}"
    if await redis.get(dedup_key):
        return

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{tax_base}/internal/mtd/auto-draft-quarterly",
                headers={"X-Internal-Token": secret},
                json={
                    "user_id": user_id,
                    "tax_year_start_year": tax_year_start_year,
                    "quarter": quarter,
                },
            )
    except httpx.HTTPError as exc:
        log.warning("auto-draft HTTP error for %s: %s", user_id, exc)
        return
    except Exception as exc:
        log.warning("auto-draft request failed for %s: %s", user_id, exc)
        return

    if resp.status_code >= 400:
        log.warning("auto-draft tax-engine %s for %s: %s", resp.status_code, user_id, (resp.text or "")[:400])
        return

    try:
        data = resp.json()
    except Exception:
        data = {}
    status = data.get("status")
    if status in ("draft_created", "skipped"):
        await redis.set(dedup_key, "1", ex=90 * 24 * 3600)
