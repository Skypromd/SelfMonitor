"""OpenAI-assisted plausibility check for regulatory diffs (RU.11)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from .diff_engine import diff_tax_rule_dicts

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


async def validate_rate_change_ai(
    old_rules: dict[str, Any],
    new_rules: dict[str, Any],
    source_url: str,
    *,
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """
    Ask the model whether diff(old, new) looks like plausible HMRC changes.
    Returns JSON dict; on failure returns rule-based fallback.
    """
    keys = ("income_tax", "national_insurance", "allowances", "student_loans", "vat", "mtd_itsa")

    def subset(r: dict[str, Any]) -> dict[str, Any]:
        return {k: r.get(k) for k in keys if k in r}

    changes = diff_tax_rule_dicts(subset(old_rules), subset(new_rules))
    if not changes:
        return {"valid": True, "action": "none", "changes": [], "note": "No diff in core blocks"}

    if not OPENAI_API_KEY:
        return {
            "valid": None,
            "action": "manual_review",
            "changes": changes[:50],
            "note": "OPENAI_API_KEY not set — manual review required",
        }

    prompt = (
        "You are a UK tax compliance engineer. Given detected JSON rule diffs from our regulatory files, "
        "assess plausibility (HMRC could have published this).\n"
        f"Source context: {source_url}\n"
        f"Diff (path, old, new):\n{json.dumps(changes[:40], indent=2)}\n\n"
        "Return a JSON object with keys: valid (boolean), severity (minor|medium|major|critical), "
        "summary (string), affected_user_groups (array of strings), recommended_actions (array of strings)."
    )
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 800,
                },
            )
            if resp.is_success:
                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(content)
    except Exception as exc:
        logger.warning("AI regulatory validation failed: %s", exc)
    return {
        "valid": None,
        "action": "manual_review",
        "changes": changes[:50],
        "note": "AI call failed — manual review",
    }
