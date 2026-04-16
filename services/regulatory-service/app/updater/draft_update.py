"""Build human-review draft items from GOV.UK parse hints vs frozen JSON (RU.13)."""
from __future__ import annotations

from typing import Any


def build_draft_items_from_parse_hints(
    tax_year: str,
    parsed: dict[str, Any],
    frozen_personal_allowance: float | None,
) -> list[dict[str, Any]]:
    """Suggest field_path updates when parser candidates diverge from JSON (heuristic)."""
    drafts: list[dict[str, Any]] = []
    if not frozen_personal_allowance:
        return drafts
    candidates = (parsed or {}).get("personal_allowance_candidates") or []
    for c in candidates:
        if abs(c - frozen_personal_allowance) > 1.0:
            drafts.append({
                "tax_year": tax_year,
                "field_path": "income_tax.personal_allowance",
                "old_value": frozen_personal_allowance,
                "new_value": c,
                "reason": f"GOV.UK parse candidate £{c:,.0f} differs from frozen £{frozen_personal_allowance:,.0f}",
            })
            break
    return drafts
