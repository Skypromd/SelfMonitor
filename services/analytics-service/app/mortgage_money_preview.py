"""
Illustrative Income & Expenditure-style monthly rollups and UK tax-year P&L summaries
from linked bank transactions (roadmap 1.5.4). Not statutory accounts or HMRC figures.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any


def _parse_tx_date(raw: Any) -> dt.date | None:
    if isinstance(raw, dt.date) and not isinstance(raw, dt.datetime):
        return raw
    if isinstance(raw, dt.datetime):
        return raw.date()
    if isinstance(raw, str) and len(raw) >= 10:
        try:
            return dt.date.fromisoformat(raw[:10])
        except ValueError:
            return None
    return None


def _parse_amount(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def uk_tax_year_label_for_date(d: dt.date) -> str:
    """Label e.g. 2024-25 for tax year containing date d (UK: 6 Apr start)."""
    y = d.year
    start = dt.date(y, 4, 6)
    if d < start:
        start = dt.date(y - 1, 4, 6)
        y0 = y - 1
    else:
        y0 = y
    y1 = y0 + 1
    return f"{y0 % 100:02d}-{y1 % 100:02d}"


def uk_tax_year_window(label: str) -> tuple[dt.date, dt.date] | None:
    """Return [6 Apr Y0, 5 Apr Y1] inclusive for label like '24-25' (two-digit / two-digit)."""
    parts = label.replace("–", "-").split("-")
    if len(parts) != 2:
        return None
    try:
        a0, a1 = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if a0 >= 100 or a1 >= 100:
        return None
    y0 = 2000 + a0
    y1 = 2000 + a1
    if y1 != y0 + 1:
        return None
    return dt.date(y0, 4, 6), dt.date(y1, 4, 5)


def aggregate_monthly_ie(
    transactions: list[dict[str, Any]],
    *,
    start: dt.date,
    end: dt.date,
) -> list[dict[str, Any]]:
    income: dict[str, float] = defaultdict(float)
    expenditure: dict[str, float] = defaultdict(float)
    for row in transactions:
        d = _parse_tx_date(row.get("date"))
        amt = _parse_amount(row.get("amount"))
        if d is None or amt is None:
            continue
        if d < start or d > end:
            continue
        key = d.strftime("%Y-%m")
        if amt >= 0:
            income[key] += amt
        else:
            expenditure[key] += -amt
    months = sorted(set(income) | set(expenditure))
    out: list[dict[str, Any]] = []
    for m in months:
        inc = round(income.get(m, 0.0), 2)
        exp = round(expenditure.get(m, 0.0), 2)
        out.append(
            {
                "month": m,
                "income_gbp": inc,
                "expenditure_gbp": exp,
                "net_gbp": round(inc - exp, 2),
            }
        )
    return out


def aggregate_tax_year_pl(
    transactions: list[dict[str, Any]],
    *,
    max_years: int = 3,
) -> list[dict[str, Any]]:
    """Gross income (positive sums) and expenses (absolute negatives) per UK tax year."""
    if max_years < 1 or max_years > 6:
        max_years = 3
    buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"income_gbp": 0.0, "expenditure_gbp": 0.0})
    for row in transactions:
        d = _parse_tx_date(row.get("date"))
        amt = _parse_amount(row.get("amount"))
        if d is None or amt is None:
            continue
        label = uk_tax_year_label_for_date(d)
        if amt >= 0:
            buckets[label]["income_gbp"] += amt
        else:
            buckets[label]["expenditure_gbp"] += -amt

    def sort_key(lab: str) -> int:
        w = uk_tax_year_window(lab)
        return w[0].year if w else 0

    ordered = sorted(buckets.keys(), key=sort_key, reverse=True)[:max_years]
    out: list[dict[str, Any]] = []
    for lab in ordered:
        inc = round(buckets[lab]["income_gbp"], 2)
        exp = round(buckets[lab]["expenditure_gbp"], 2)
        window = uk_tax_year_window(lab)
        out.append(
            {
                "tax_year": lab,
                "period_start": window[0].isoformat() if window else None,
                "period_end": window[1].isoformat() if window else None,
                "income_gbp": inc,
                "expenditure_gbp": exp,
                "net_profit_gbp": round(inc - exp, 2),
            }
        )
    return list(reversed(out))


def build_mortgage_money_preview(
    transactions: list[dict[str, Any]],
    *,
    months: int = 12,
    tax_years: int = 3,
) -> dict[str, Any]:
    months = max(1, min(36, months))
    tax_years = max(1, min(6, tax_years))
    end = dt.date.today()
    start = end - dt.timedelta(days=int(months * 31))
    monthly = aggregate_monthly_ie(transactions, start=start, end=end)
    tax_summary = aggregate_tax_year_pl(transactions, max_years=tax_years)
    disclaimer = (
        "Illustrative cash movements derived from linked bank transactions in MyNetTax only. "
        "Not statutory accounts, not audited figures, and not a substitute for HMRC Self Assessment / "
        "company accounts. Brokers and lenders may require certified documents."
    )
    return {
        "disclaimer": disclaimer,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "months_requested": months,
        "monthly_income_and_expenditure": monthly,
        "tax_year_summaries": tax_summary,
    }
