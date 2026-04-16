"""
Thin helpers for estimating tax from a rules dict (full product logic lives in tax-engine).

Use for admin previews / sanity only.
"""
from __future__ import annotations

from typing import Any


def estimate_income_tax_from_rules(taxable_after_pa: float, rules: dict[str, Any]) -> float:
    bands = (rules.get("income_tax") or {}).get("bands") or []
    tax = 0.0
    for band in sorted(bands, key=lambda b: float(b["from"])):
        lo = float(band["from"])
        hi = float(band["to"]) if band.get("to") is not None else float("inf")
        chunk = max(0.0, min(taxable_after_pa, hi) - lo)
        tax += chunk * float(band["rate"])
    return round(tax, 2)
