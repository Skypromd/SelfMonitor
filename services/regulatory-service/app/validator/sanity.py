from __future__ import annotations

from typing import Any


def validate_tax_year_rules(rules: dict[str, Any]) -> list[str]:
    """Return human-readable issues; empty list means checks passed."""
    issues: list[str] = []
    ty = rules.get("tax_year")
    if not ty:
        issues.append("missing tax_year")

    it = rules.get("income_tax") or {}
    pa = it.get("personal_allowance")
    if pa is not None:
        if not isinstance(pa, (int, float)) or pa <= 0 or pa > 50000:
            issues.append(f"income_tax.personal_allowance implausible: {pa!r}")

    taper = it.get("personal_allowance_taper_threshold")
    if taper is not None and pa is not None:
        if taper <= float(pa):
            issues.append("personal_allowance_taper_threshold should exceed personal_allowance")

    bands = it.get("bands") or []
    if not bands:
        issues.append("income_tax.bands empty")
    else:
        for b in bands:
            rate = b.get("rate")
            if rate is None or not isinstance(rate, (int, float)) or rate < 0 or rate > 0.6:
                issues.append(f"band rate out of range: {b!r}")
            bf = b.get("from")
            bt = b.get("to")
            if bf is not None and bt is not None and float(bt) < float(bf):
                issues.append(f"band 'to' before 'from': {b!r}")

    ni = rules.get("national_insurance") or {}
    c4 = ni.get("class_4") or {}
    for fld in ("lower_profits_limit", "upper_profits_limit"):
        v = c4.get(fld)
        if v is not None and (not isinstance(v, (int, float)) or v < 0 or v > 500000):
            issues.append(f"class_4.{fld} implausible: {v!r}")
    lpl = c4.get("lower_profits_limit")
    upl = c4.get("upper_profits_limit")
    if lpl is not None and upl is not None and float(upl) <= float(lpl):
        issues.append("class_4 upper_profits_limit must exceed lower_profits_limit")

    mr = c4.get("main_rate")
    ar = c4.get("additional_rate")
    if mr is not None and (mr < 0 or mr > 0.2):
        issues.append(f"class_4.main_rate implausible: {mr!r}")
    if ar is not None and (ar < 0 or ar > 0.2):
        issues.append(f"class_4.additional_rate implausible: {ar!r}")

    c2 = ni.get("class_2") or {}
    wk = c2.get("weekly_rate_voluntary", c2.get("weekly_rate"))
    if wk is not None and (wk < 0 or wk > 50):
        issues.append(f"class_2 weekly rate implausible: {wk!r}")

    mtd = rules.get("mtd_itsa") or {}
    th = mtd.get("threshold")
    if th is not None and (th < 0 or th > 500000):
        issues.append(f"mtd_itsa.threshold implausible: {th!r}")

    return issues
