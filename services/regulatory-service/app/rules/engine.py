"""Which rule snapshot applies on a calendar date (RU rules engine baseline)."""
from __future__ import annotations

from datetime import date
from typing import Any


def tax_year_for_date(d: date) -> str:
    if d >= date(d.year, 4, 6):
        return f"{d.year}-{str(d.year + 1)[2:]}"
    return f"{d.year - 1}-{str(d.year)[2:]}"


def core_subset_for_diff(rules: dict[str, Any]) -> dict[str, Any]:
    keys = ("income_tax", "national_insurance", "allowances", "mtd_itsa", "vat", "student_loans")
    return {k: rules[k] for k in keys if k in rules}
