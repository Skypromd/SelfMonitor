"""
Rolling profit aggregates from bank transactions (net = sum of amounts; expenses negative).

Excludes receipt-draft-* placeholder rows to approximate realised bank activity.
"""

from __future__ import annotations

import datetime
from typing import Any


def uk_tax_year_start_on(d: datetime.date) -> datetime.date:
    y = d.year
    if d.month < 4 or (d.month == 4 and d.day < 6):
        return datetime.date(y - 1, 4, 6)
    return datetime.date(y, 4, 6)


def monday_of(d: datetime.date) -> datetime.date:
    return d - datetime.timedelta(days=d.weekday())


def _amount(t: dict[str, Any]) -> float:
    try:
        return float(t.get("amount") or 0)
    except (TypeError, ValueError):
        return 0.0


def _txn_date(t: dict[str, Any]) -> datetime.date | None:
    raw = t.get("date")
    if raw is None:
        return None
    try:
        return datetime.date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _is_bank_row(t: dict[str, Any]) -> bool:
    pid = str(t.get("provider_transaction_id") or "")
    return not pid.startswith("receipt-draft-")


def _net_between(rows: list[dict[str, Any]], start: datetime.date, end: datetime.date) -> float:
    s = 0.0
    for t in rows:
        d = _txn_date(t)
        if d is None or d < start or d > end:
            continue
        s += _amount(t)
    return round(s, 2)


def build_profit_pulse(
    transactions: list[dict[str, Any]],
    *,
    today: datetime.date | None = None,
) -> dict[str, Any]:
    today = today or datetime.date.today()
    rows = [t for t in transactions if isinstance(t, dict) and _is_bank_row(t)]

    profit_today = _net_between(rows, today, today)

    m0 = monday_of(today)
    w_end = m0 + datetime.timedelta(days=6)
    profit_week = _net_between(rows, m0, w_end)

    ws_ly = m0 - datetime.timedelta(days=364)
    we_ly = w_end - datetime.timedelta(days=364)
    profit_week_prior_year = _net_between(rows, ws_ly, we_ly)
    yoy_week_delta = round(profit_week - profit_week_prior_year, 2)

    weekly: list[dict[str, Any]] = []
    for k in range(7, -1, -1):
        ws = m0 - datetime.timedelta(weeks=k)
        we = ws + datetime.timedelta(days=6)
        inc = 0.0
        exp = 0.0
        net = 0.0
        for t in rows:
            d = _txn_date(t)
            if d is None or d < ws or d > we:
                continue
            a = _amount(t)
            net += a
            if a > 0:
                inc += a
            else:
                exp += -a
        weekly.append(
            {
                "week_start": ws.isoformat(),
                "week_end": we.isoformat(),
                "income_gbp": round(inc, 2),
                "expenses_gbp": round(exp, 2),
                "profit_gbp": round(net, 2),
            }
        )

    ty_start = uk_tax_year_start_on(today)
    profit_tax_year_to_date = _net_between(rows, ty_start, today)

    disclaimer = (
        "Profit figures are net cash movement in linked bank data (not accrual accounts). "
        "Tax estimate is from tax-engine when requested — verify before filing."
    )

    return {
        "as_of": today.isoformat(),
        "profit_today_gbp": profit_today,
        "profit_week_gbp": profit_week,
        "profit_tax_year_to_date_gbp": profit_tax_year_to_date,
        "weekly": weekly,
        "yoy_week_profit_delta_gbp": yoy_week_delta,
        "prior_year_same_week_profit_gbp": profit_week_prior_year,
        "disclaimer": disclaimer,
        "transaction_rows_used": len(rows),
    }
