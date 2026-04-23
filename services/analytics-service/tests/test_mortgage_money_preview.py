"""Mortgage money preview (I&E + tax-year rollups from transactions)."""

from app.mortgage_money_preview import (
    aggregate_monthly_ie,
    aggregate_tax_year_pl,
    build_mortgage_money_preview,
    uk_tax_year_label_for_date,
    uk_tax_year_window,
)


def test_uk_tax_year_label():
    from datetime import date

    assert uk_tax_year_label_for_date(date(2025, 4, 5)) == "24-25"
    assert uk_tax_year_label_for_date(date(2025, 4, 6)) == "25-26"


def test_uk_tax_year_window():
    w = uk_tax_year_window("24-25")
    assert w is not None
    assert w[0].isoformat() == "2024-04-06"
    assert w[1].isoformat() == "2025-04-05"


def test_aggregate_monthly_ie():
    tx = [
        {"date": "2025-01-10", "amount": 1000},
        {"date": "2025-01-20", "amount": -200},
        {"date": "2025-02-01", "amount": 500},
    ]
    from datetime import date

    rows = aggregate_monthly_ie(tx, start=date(2025, 1, 1), end=date(2025, 12, 31))
    assert len(rows) == 2
    jan = next(r for r in rows if r["month"] == "2025-01")
    assert jan["income_gbp"] == 1000.0
    assert jan["expenditure_gbp"] == 200.0
    assert jan["net_gbp"] == 800.0


def test_aggregate_tax_year_pl():
    tx = [
        {"date": "2024-06-01", "amount": 12000},
        {"date": "2024-06-15", "amount": -3000},
        {"date": "2025-01-01", "amount": 6000},
    ]
    rows = aggregate_tax_year_pl(tx, max_years=3)
    labels = {r["tax_year"] for r in rows}
    assert "24-25" in labels


def test_build_mortgage_money_preview_disclaimer():
    raw = build_mortgage_money_preview([], months=6, tax_years=2)
    assert "Illustrative" in raw["disclaimer"]
    assert raw["months_requested"] == 6
    assert raw["monthly_income_and_expenditure"] == []
    assert raw["tax_year_summaries"] == []
