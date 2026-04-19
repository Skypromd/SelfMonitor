"""
UK self-employment tax-saving hints from static rules + simple transaction patterns.

Not tax advice — users must verify with HMRC guidance or an accountant each year.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Any


def filter_transactions_for_tax_year(
    transactions: list[dict[str, Any]],
    start: datetime.date | None,
    end: datetime.date | None,
) -> list[dict[str, Any]]:
    if start is None or end is None:
        return list(transactions)
    out: list[dict[str, Any]] = []
    for t in transactions:
        raw = t.get("date")
        if raw is None:
            continue
        try:
            d = datetime.date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
        if start <= d <= end:
            out.append(t)
    return out

# Illustrative maxima for UI only (tax year rules change — verify gov.uk).
_HOME_OFFICE_FLAT_PER_WEEK_GBP = 6.0
_WEEKS_PER_YEAR = 52
_HOME_OFFICE_FLAT_ANNUAL_GBP = round(_HOME_OFFICE_FLAT_PER_WEEK_GBP * _WEEKS_PER_YEAR, 2)

_STATIC_TIPS: list[dict[str, Any]] = [
    {
        "id": "trading_allowance",
        "title": "£1,000 trading allowance",
        "detail": (
            "If gross trading income is under £1,000 you may use the trading allowance instead of "
            "detailed expenses — see HMRC HS325. Not suitable for everyone."
        ),
        "category": "static",
        "potential_saving_gbp": None,
        "priority": 30,
    },
    {
        "id": "home_office_flat",
        "title": "Simplified home office (flat rate)",
        "detail": (
            f"You can claim £{_HOME_OFFICE_FLAT_PER_WEEK_GBP:.0f}/week flat rate when working from home "
            f"(no receipts) — up to ~£{_HOME_OFFICE_FLAT_ANNUAL_GBP:.0f}/year if eligible all year. "
            "Check HMRC simplified expenses for current rules."
        ),
        "category": "static",
        "potential_saving_gbp": _HOME_OFFICE_FLAT_ANNUAL_GBP,
        "priority": 25,
    },
    {
        "id": "mileage_rates",
        "title": "Business mileage (AMAP-style)",
        "detail": (
            "HMRC-approved mileage rates for cars are often quoted as 45p/mile for the first 10,000 "
            "business miles in a tax year (then a lower rate). Keep a contemporaneous log."
        ),
        "category": "static",
        "potential_saving_gbp": None,
        "priority": 24,
    },
    {
        "id": "phone_internet_split",
        "title": "Phone and broadband — business share",
        "detail": (
            "Apportion line rental and broadband by reasonable business use %; keep a short note of your method."
        ),
        "category": "static",
        "potential_saving_gbp": None,
        "priority": 22,
    },
]


def _txn_category(t: dict[str, Any]) -> str:
    c = t.get("category")
    if isinstance(c, str) and c.strip():
        return c.strip().lower().replace(" ", "_")
    return ""


def _txn_amount(t: dict[str, Any]) -> float:
    try:
        return float(t.get("amount") or 0)
    except (TypeError, ValueError):
        return 0.0


def build_tax_savings_tips(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    tips: list[dict[str, Any]] = []
    tips.extend(dict(x) for x in _STATIC_TIPS)

    expenses_by_cat: defaultdict[str, float] = defaultdict(float)
    n_expense = 0
    for t in transactions:
        amt = _txn_amount(t)
        if amt >= 0:
            continue
        n_expense += 1
        cat = _txn_category(t)
        if cat:
            expenses_by_cat[cat] += abs(amt)

    total_expenses = sum(expenses_by_cat.values())

    travel_like = (
        expenses_by_cat.get("travel", 0)
        + expenses_by_cat.get("fuel", 0)
        + expenses_by_cat.get("mileage", 0)
        + expenses_by_cat.get("transport", 0)
    )
    has_home_signals = (
        expenses_by_cat.get("home_office", 0) > 0
        or expenses_by_cat.get("office", 0) > 50
    )

    if total_expenses >= 800 and travel_like < 150 and not has_home_signals:
        tips.append(
            {
                "id": "pattern_mileage_log",
                "title": "Low travel spend vs total expenses",
                "detail": (
                    "Your categorised travel/fuel is modest relative to total expenses. If you drive for work, "
                    "a mileage log may capture costs that card descriptions miss."
                ),
                "category": "personalized",
                "potential_saving_gbp": None,
                "priority": 80,
            }
        )

    if total_expenses >= 500 and not has_home_signals:
        tips.append(
            {
                "id": "pattern_home_office",
                "title": "Home office allowance",
                "detail": (
                    f"If you work from home regularly, the £{_HOME_OFFICE_FLAT_PER_WEEK_GBP:.0f}/week simplified "
                    f"rate could be ~£{_HOME_OFFICE_FLAT_ANNUAL_GBP:.0f}/year without receipts — "
                    "we did not see a strong home-office category in your expenses."
                ),
                "category": "personalized",
                "potential_saving_gbp": _HOME_OFFICE_FLAT_ANNUAL_GBP,
                "priority": 85,
            }
        )

    subs = expenses_by_cat.get("subscriptions", 0) + expenses_by_cat.get("software", 0)
    if subs >= 400:
        tips.append(
            {
                "id": "pattern_subscriptions_review",
                "title": "Subscriptions and software",
                "detail": (
                    f"You have ~£{subs:,.0f} in subscription/software-type categories. "
                    "Mark which tools are wholly for business vs mixed use."
                ),
                "category": "personalized",
                "potential_saving_gbp": None,
                "priority": 55,
            }
        )

    phone = expenses_by_cat.get("phone", 0) + expenses_by_cat.get("internet", 0) + expenses_by_cat.get("utilities", 0)
    if phone >= 200:
        tips.append(
            {
                "id": "pattern_comms_split",
                "title": "Communications and utilities",
                "detail": (
                    f"~£{phone:,.0f} in phone/internet/utilities — consider documenting your business-use %."
                ),
                "category": "personalized",
                "potential_saving_gbp": None,
                "priority": 60,
            }
        )

    tips.sort(key=lambda x: (-int(x.get("priority", 0)), x.get("id", "")))

    disclaimer = (
        "These hints are for planning only — not professional tax advice. "
        "Rules and thresholds change; confirm with HMRC or a qualified adviser."
    )

    return {
        "tips": tips,
        "disclaimer": disclaimer,
        "transaction_count_used": len(transactions),
        "expense_lines_used": n_expense,
    }
