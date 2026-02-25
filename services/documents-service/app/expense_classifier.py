from __future__ import annotations

from typing import Optional

DEDUCTIBLE_RECEIPT_CATEGORIES = {"transport", "subscriptions", "office_supplies"}

KEYWORD_CATEGORY_RULES: dict[str, str] = {
    "tfl": "transport",
    "trainline": "transport",
    "uber": "transport",
    "bolt": "transport",
    "tesco": "office_supplies",
    "sainsbury": "office_supplies",
    "asda": "office_supplies",
    "lidl": "office_supplies",
    "staples": "office_supplies",
    "ryman": "office_supplies",
    "amazon business": "office_supplies",
    "adobe": "subscriptions",
    "notion": "subscriptions",
    "xero": "subscriptions",
    "quickbooks": "subscriptions",
    "google workspace": "subscriptions",
    "microsoft 365": "subscriptions",
    "costa": "food_and_drink",
    "pret": "food_and_drink",
    "starbucks": "food_and_drink",
    "restaurant": "food_and_drink",
}

EXPENSE_ARTICLE_BY_CATEGORY: dict[str, str] = {
    "transport": "travel_costs",
    "subscriptions": "software_subscriptions",
    "office_supplies": "office_supplies",
    "food_and_drink": "meals_and_entertainment",
    "income": "non_expense_income",
}


def suggest_category_from_keywords(description: str) -> Optional[str]:
    normalized = description.strip().lower()
    if not normalized:
        return None

    for keyword, category in KEYWORD_CATEGORY_RULES.items():
        if keyword in normalized:
            return category
    return None


def to_expense_article(category: Optional[str]) -> tuple[Optional[str], Optional[bool]]:
    if not category:
        return None, None
    article = EXPENSE_ARTICLE_BY_CATEGORY.get(category, "other")
    return article, category in DEDUCTIBLE_RECEIPT_CATEGORIES
