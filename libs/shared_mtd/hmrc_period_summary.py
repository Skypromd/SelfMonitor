"""Shared HMRC MTD ITSA self-employment period summary body (periodic update shape).

Used by mtd-agent (direct test-api) and kept aligned with tax-engine / integrations
quarterly payload fields for turnover and allowable expenses.
"""

from __future__ import annotations

from typing import Any


def build_mtd_self_employment_period_summary(
    *,
    period_start_iso: str,
    period_end_iso: str,
    turnover: float,
    allowable_expenses: float,
    other_income: float = 0.0,
    cost_of_goods: float = 0.0,
) -> dict[str, Any]:
    return {
        "periodDates": {
            "periodStartDate": period_start_iso,
            "periodEndDate": period_end_iso,
        },
        "periodIncome": {
            "turnover": round(float(turnover), 2),
            "other": round(float(other_income), 2),
        },
        "periodExpenses": {
            "costOfGoods": round(float(cost_of_goods), 2),
            "allowableExpenses": round(float(allowable_expenses), 2),
        },
    }
