"""
Rule-based quick intent for voice / typed expense phrases (roadmap 2.2).

Maps natural language to {amount, category, currency} — UK-oriented categories
aligned with common MyNetTax expense labels.
"""

from __future__ import annotations

import re
from typing import Any

_AMOUNT_RE = re.compile(
    r"(?:£|gbp\s*)?\s*(\d+(?:[.,]\d{1,2})?)\s*(?:pounds?|gbp|£)?",
    re.I,
)
_NUM = re.compile(r"(\d+(?:[.,]\d{1,2})?)")


def _parse_amount(text: str) -> float | None:
    m = _AMOUNT_RE.search(text)
    if not m:
        m2 = _NUM.search(text)
        if not m2:
            return None
        raw = m2.group(1).replace(",", ".")
    else:
        raw = m.group(1).replace(",", ".")
    try:
        v = float(raw)
    except ValueError:
        return None
    if v <= 0 or v > 1_000_000:
        return None
    return v


def _category_for_lang(text: str, lang: str) -> str | None:
    t = text.lower()
    _ = (lang or "en").lower()[:2]

    fuel_kw = (
        "fuel",
        "petrol",
        "gas",
        "diesel",
        "benzyn",
        "benzina",
        "motorina",
        "paliwo",
        "combustibil",
        "бензин",
        "паливо",
        "пальне",
    )
    food_kw = (
        "lunch",
        "food",
        "meal",
        "restaurant",
        "jedzen",
        "mâncare",
        "mancare",
        "pranz",
        "prânz",
        "obiad",
        "mic dejun",
        "еда",
        "їжа",
    )
    train_kw = (
        "train",
        "tube",
        "metro",
        "pociąg",
        "tren",
        "поїзд",
        "метро",
        "metrou",
        "cale ferata",
    )
    office_kw = ("office", "supplies", "biuro", "birou", "канц", "папір", "birou de lucru")

    if any(k in t for k in fuel_kw):
        return "Fuel"
    if any(k in t for k in food_kw):
        return "Meals"
    if any(k in t for k in train_kw):
        return "Travel"
    if any(k in t for k in office_kw):
        return "Office costs"
    if "parking" in t or "parkow" in t or "parcare" in t:
        return "Motor expenses"
    if "hotel" in t or "airbnb" in t:
        return "Accommodation"
    return None


def parse_expense_intent(text: str, language: str = "en") -> dict[str, Any] | None:
    """
    Parse a short phrase like 'paid 50 pounds for petrol' → structured intent.
    Returns None if amount or category cannot be inferred.
    """
    raw = (text or "").strip()
    if len(raw) < 3:
        return None
    amount = _parse_amount(raw)
    category = _category_for_lang(raw, language)
    if amount is None or category is None:
        return None
    return {
        "amount": amount,
        "category": category,
        "currency": "GBP",
        "confidence": "rule_based",
    }
