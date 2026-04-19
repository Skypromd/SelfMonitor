import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tax_savings_tips import (
    build_tax_savings_tips,
    filter_transactions_for_tax_year,
)


def test_filter_tax_year():
    txs = [
        {"date": "2024-01-01", "amount": -50, "category": "fuel"},
        {"date": "2025-06-01", "amount": -30, "category": "fuel"},
    ]
    start = datetime.date(2025, 4, 6)
    end = datetime.date(2026, 4, 5)
    f = filter_transactions_for_tax_year(txs, start, end)
    assert len(f) == 1
    assert f[0]["date"] == "2025-06-01"


def test_personalized_home_office_when_no_home_category():
    txs = []
    for _ in range(20):
        txs.append({"date": "2025-08-01", "amount": -100, "category": "software"})
    r = build_tax_savings_tips(txs)
    ids = [t["id"] for t in r["tips"]]
    assert "pattern_home_office" in ids
    assert r["expense_lines_used"] == 20


def test_static_tips_always_present():
    r = build_tax_savings_tips([])
    assert any(t["id"] == "trading_allowance" for t in r["tips"])
