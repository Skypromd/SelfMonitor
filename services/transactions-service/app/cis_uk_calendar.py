"""UK tax calendar for CIS: tax months run 6th–5th; month 1 starts 6 April."""
from __future__ import annotations

import datetime
import re


def tax_year_starting_april_year_for_date(d: datetime.date) -> int:
    if d >= datetime.date(d.year, 4, 6):
        return d.year
    return d.year - 1


def uk_tax_month_starts(tax_year_start: int) -> list[datetime.date]:
    ty = tax_year_start
    return [
        datetime.date(ty, 4, 6),
        datetime.date(ty, 5, 6),
        datetime.date(ty, 6, 6),
        datetime.date(ty, 7, 6),
        datetime.date(ty, 8, 6),
        datetime.date(ty, 9, 6),
        datetime.date(ty, 10, 6),
        datetime.date(ty, 11, 6),
        datetime.date(ty, 12, 6),
        datetime.date(ty + 1, 1, 6),
        datetime.date(ty + 1, 2, 6),
        datetime.date(ty + 1, 3, 6),
    ]


def uk_tax_month_for_date(d: datetime.date) -> tuple[int, int]:
    """
    Returns (tax_year_starting_april_year, tax_month_1_to_12).
    Tax month 1 = 6 Apr–5 May of that tax year start.
    """
    ty = tax_year_starting_april_year_for_date(d)
    starts = uk_tax_month_starts(ty)
    for i in range(12):
        start = starts[i]
        if i < 11:
            end = starts[i + 1] - datetime.timedelta(days=1)
        else:
            end = datetime.date(ty + 1, 4, 5)
        if start <= d <= end:
            return ty, i + 1
    return ty, 12


def contractor_key_from_label(label: str | None) -> str:
    raw = (label or "").strip().lower()
    raw = re.sub(r"\s+", " ", raw)
    raw = re.sub(r"[^a-z0-9\s\-]", "", raw)
    key = raw[:80] if raw else "unknown"
    return key or "unknown"


def format_tax_month_label(tax_year_start: int, tax_month: int) -> str:
    return f"{tax_year_start}/{tax_year_start + 1} M{tax_month}"
