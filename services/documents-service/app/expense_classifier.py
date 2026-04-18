from __future__ import annotations

from typing import Optional

# HMRC SA103F-aligned codes (same set as regulatory-service allowable_expenses.categories).
HMRC_ALLOWABLE_EXPENSE_CODES = frozenset({
    "office_costs",
    "travel",
    "clothing",
    "staff_costs",
    "stock_materials",
    "financial_costs",
    "premises",
    "advertising",
    "interest",
    "professional_fees",
    "depreciation",
    "other_expenses",
    "use_of_home",
    "vehicle_mileage",
    "subscriptions",
    "training",
    "equipment",
    "telephone",
    "legal",
    "accounting",
    "electric_vehicle",
    "pension",
    "health_safety",
    "bank_charges",
})

_CATEGORY_ALIASES: dict[str, str] = {
    "transport": "travel",
    "fuel": "travel",
    "mileage": "vehicle_mileage",
    "office_supplies": "office_costs",
    "office": "office_costs",
    "stationery": "office_costs",
    "professional_services": "professional_fees",
    "marketing": "advertising",
    "promotion": "advertising",
    "rent": "premises",
    "utilities": "premises",
    "insurance": "financial_costs",
    "software": "equipment",
    "tools": "equipment",
    "hardware": "equipment",
}

DEDUCTIBLE_RECEIPT_CATEGORIES = HMRC_ALLOWABLE_EXPENSE_CODES | set(_CATEGORY_ALIASES.keys())

KEYWORD_CATEGORY_RULES: dict[str, str] = {
    "tfl": "transport",
    "trainline": "transport",
    "uber": "transport",
    "bolt": "transport",
    "shell": "fuel",
    "bp fuel": "fuel",
    "tesco": "office_supplies",
    "sainsbury": "office_supplies",
    "asda": "office_supplies",
    "lidl": "office_supplies",
    "staples": "office_supplies",
    "ryman": "office_supplies",
    "amazon business": "office_supplies",
    "openrent": "premises",
    "letting agent": "premises",
    "adobe": "subscriptions",
    "notion": "subscriptions",
    "xero": "subscriptions",
    "quickbooks": "subscriptions",
    "google workspace": "subscriptions",
    "microsoft 365": "subscriptions",
    "accountant": "accounting",
    "bookkeeping": "accounting",
    "solicitor": "legal",
    "aviva business": "financial_costs",
    "simply business": "financial_costs",
    "costa": "food_and_drink",
    "pret": "food_and_drink",
    "starbucks": "food_and_drink",
    "restaurant": "food_and_drink",
}

EXPENSE_ARTICLE_BY_CATEGORY: dict[str, str] = {
    "travel": "travel_costs",
    "vehicle_mileage": "travel_costs",
    "electric_vehicle": "travel_costs",
    "office_costs": "office_costs",
    "subscriptions": "software_subscriptions",
    "premises": "premises_running_costs",
    "use_of_home": "use_of_home",
    "advertising": "advertising_costs",
    "professional_fees": "professional_fees",
    "legal": "professional_fees",
    "accounting": "professional_fees",
    "training": "training_costs",
    "staff_costs": "staff_costs",
    "stock_materials": "cost_of_goods",
    "financial_costs": "finance_and_insurance",
    "bank_charges": "bank_charges",
    "interest": "interest",
    "telephone": "communications",
    "equipment": "equipment",
    "depreciation": "capital_allowances",
    "clothing": "protective_clothing",
    "health_safety": "health_and_safety",
    "pension": "pension_costs",
    "other_expenses": "other_business",
    "food_and_drink": "meals_and_entertainment",
    "income": "non_expense_income",
    "transport": "travel_costs",
    "office_supplies": "office_costs",
    "fuel": "travel_costs",
}


def suggest_category_from_keywords(description: str) -> Optional[str]:
    normalized = description.strip().lower()
    if not normalized:
        return None

    for keyword, category in KEYWORD_CATEGORY_RULES.items():
        if keyword in normalized:
            return category
    return None


def canonical_hmrc_expense_code(category: Optional[str]) -> Optional[str]:
    """Map classifier slug to regulatory HMRC allowable expense `code`, if known."""
    if not category:
        return None
    key = category.strip()
    if not key:
        return None
    canonical = _CATEGORY_ALIASES.get(key, key)
    if canonical in HMRC_ALLOWABLE_EXPENSE_CODES:
        return canonical
    return None


def to_expense_article(category: Optional[str]) -> tuple[Optional[str], Optional[bool]]:
    if not category:
        return None, None
    canonical = _CATEGORY_ALIASES.get(category, category)
    article = EXPENSE_ARTICLE_BY_CATEGORY.get(
        canonical,
        EXPENSE_ARTICLE_BY_CATEGORY.get(category, "other"),
    )
    deductible = canonical in HMRC_ALLOWABLE_EXPENSE_CODES
    return article, deductible
