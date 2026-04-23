"""Tests for rule-based expense intent parser."""

from app.expense_intent import parse_expense_intent


def test_parse_en_fuel():
    r = parse_expense_intent("I paid £50 for petrol yesterday", "en")
    assert r is not None
    assert r["amount"] == 50.0
    assert r["category"] == "Fuel"
    assert r["currency"] == "GBP"


def test_parse_en_meals():
    r = parse_expense_intent("paid 12.50 lunch", "en")
    assert r is not None
    assert r["amount"] == 12.5
    assert r["category"] == "Meals"


def test_parse_no_category():
    assert parse_expense_intent("paid 99", "en") is None


def test_parse_pl_fuel():
    r = parse_expense_intent("zapłaciłem 40 zł za paliwo", "pl")
    assert r is not None
    assert r["category"] == "Fuel"


def test_parse_ro_meals():
    r = parse_expense_intent("am platit 35 lei restaurant", "ro")
    assert r is not None
    assert r["amount"] == 35.0
    assert r["category"] == "Meals"


def test_parse_ro_train():
    r = parse_expense_intent("bilet metrou 8 lei", "ro")
    assert r is not None
    assert r["category"] == "Travel"


def test_parse_uk_lang_fuel():
    r = parse_expense_intent("spent 20 pounds on паливо", "uk")
    assert r is not None
    assert r["category"] == "Fuel"
