"""Helpers for extended UK /calculate (combined income, allowances, credits)."""
from __future__ import annotations

import copy
from typing import Any, List, Optional


def normalize_student_loan_plan(plan: Optional[str]) -> Optional[str]:
    if not plan:
        return None
    s = plan.strip().lower().replace("-", "_")
    aliases = {
        "plan1": "plan_1",
        "plan2": "plan_2",
        "plan4": "plan_4",
        "plan5": "plan_5",
        "postgrad": "postgraduate",
    }
    return aliases.get(s, s)


def student_loan_repayment_annual(
    total_income: float,
    plan: Optional[str],
    student_loans: dict[str, Any],
) -> float:
    key = normalize_student_loan_plan(plan)
    if not key or key not in student_loans:
        return 0.0
    row = student_loans[key]
    th = float(row.get("threshold", 0))
    r = float(row.get("rate", 0))
    return max(0.0, total_income - th) * r


def expenses_with_trading_allowance(
    gross_income: float,
    expenses: float,
    use_allowance: bool,
    allowance_cap: float,
) -> float:
    if not use_allowance:
        return expenses
    return max(expenses, min(float(allowance_cap), float(gross_income)))


def gift_aid_extend_basic_band(bands: list[dict[str, Any]], net_donations_gbp: float) -> list[dict[str, Any]]:
    """Extend basic / higher thresholds by net * 0.25 (gross-up at basic rate). Scotland: skip if bands not standard names."""
    if net_donations_gbp <= 0:
        return bands
    ext = float(net_donations_gbp) * 0.25
    out: list[dict[str, Any]] = []
    for b in bands:
        bc = copy.deepcopy(b)
        name = bc.get("name", "")
        if name == "basic" and bc.get("to") is not None:
            bc["to"] = float(bc["to"]) + ext
        elif name in ("higher", "intermediate", "advanced") and bc.get("from") is not None:
            bc["from"] = float(bc["from"]) + ext
        elif name == "additional" and bc.get("from") is not None:
            bc["from"] = float(bc["from"]) + ext
        out.append(bc)
    return out


def rough_employee_class1_annual(gross_salary: float) -> float:
    """Approximate annual Class 1 employee NI (not weekly pro-rata)."""
    if gross_salary <= 12_570:
        return 0.0
    main_slice = max(min(gross_salary, 50_270) - 12_570, 0.0)
    ni = main_slice * 0.08
    if gross_salary > 50_270:
        ni += (gross_salary - 50_270) * 0.02
    return ni


def payments_on_account_each(
    income_tax: float,
    class4: float,
    student_loan: float,
    *,
    threshold: float = 1000.0,
) -> float:
    base = max(0.0, income_tax + class4 + student_loan)
    if base <= threshold:
        return 0.0
    return round(base * 0.5, 2)


def build_sa103_box_hints(summary_by_category: list[dict[str, Any]]) -> dict[str, float]:
    """Map common category keys to SA103F-style box totals for disclosure."""
    box_map = {
        "office_supplies": 17,
        "office_costs": 17,
        "stationery": 17,
        "transport": 18,
        "travel": 18,
        "fuel": 18,
        "mileage": 18,
        "vehicle_mileage": 18,
        "clothing": 19,
        "uniform": 19,
        "staff_costs": 20,
        "wages": 20,
        "stock": 21,
        "materials": 21,
        "stock_materials": 21,
        "cost_of_goods": 21,
        "insurance": 22,
        "financial_costs": 22,
        "bank_charges": 22,
        "rent": 23,
        "utilities": 23,
        "premises": 23,
        "home_office": 23,
        "use_of_home": 23,
        "advertising": 24,
        "marketing": 24,
        "interest": 25,
        "professional_fees": 26,
        "legal": 26,
        "accounting": 26,
        "depreciation": 27,
        "equipment": 27,
    }
    boxes: dict[int, float] = {}
    for row in summary_by_category:
        cat = str(row.get("category", ""))
        amt = float(row.get("total_amount", 0))
        if amt >= 0:
            continue
        spend = abs(amt)
        box = box_map.get(cat, 28)
        boxes[box] = boxes.get(box, 0.0) + spend
    return {f"box_{k}": round(v, 2) for k, v in sorted(boxes.items())}


def build_estimate_disclaimers(
    *,
    regulatory_source: str,
    region: str,
    gift_aid_net_gbp: float,
    savings_interest_gross_gbp: float,
    dividend_income_gross_gbp: float,
    chargeable_gains_gbp: float,
    is_non_uk_resident: bool,
) -> List[str]:
    """User-facing caveats for /calculate (not legal advice)."""
    lines = [
        "This response is a planning estimate only; final tax follows HMRC Self Assessment and your filed return.",
    ]
    if regulatory_source in ("fallback_defaults", "empty_response", "invalid_response", "stale_cache"):
        lines.append(
            "Tax rates for this run did not come from a fresh regulatory-service snapshot "
            f"(source: {regulatory_source}); figures may deviate from live HMRC rules."
        )
    elif regulatory_source == "cache":
        lines.append("Rates were taken from a short-lived cache of regulatory-service data.")
    if savings_interest_gross_gbp > 0:
        lines.append(
            "Savings interest uses a simplified income stack (not full Personal Savings Allowance / starter savings rate)."
        )
    if region == "scotland" and gift_aid_net_gbp > 0:
        lines.append("Gift Aid band extension for Scotland is not fully modelled in this estimate.")
    if dividend_income_gross_gbp > 0 or chargeable_gains_gbp > 0:
        lines.append("Dividend and CGT components use calculator approximations; complex cases need professional advice.")
    if is_non_uk_resident:
        lines.append("Non-UK resident tax rules are not modelled; assume UK residency unless you override.")
    return lines
