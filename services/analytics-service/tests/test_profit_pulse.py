import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.profit_pulse import build_profit_pulse


def test_excludes_receipt_drafts():
    today = datetime.date(2025, 6, 10)
    txs = [
        {"date": today.isoformat(), "amount": 100, "provider_transaction_id": "x1"},
        {
            "date": today.isoformat(),
            "amount": 999,
            "provider_transaction_id": "receipt-draft-abc",
        },
    ]
    r = build_profit_pulse(txs, today=today)
    assert r["profit_today_gbp"] == 100.0
    assert r["transaction_rows_used"] == 1


def test_week_and_buckets():
    mon = datetime.date(2025, 6, 9)
    txs = [
        {"date": mon.isoformat(), "amount": 200, "provider_transaction_id": "a"},
        {"date": (mon + datetime.timedelta(days=1)).isoformat(), "amount": -50, "provider_transaction_id": "b"},
    ]
    r = build_profit_pulse(txs, today=mon + datetime.timedelta(days=2))
    assert r["profit_week_gbp"] == 150.0
    assert len(r["weekly"]) == 8
    last = r["weekly"][-1]
    assert last["profit_gbp"] == 150.0
    assert last["income_gbp"] == 200.0
    assert last["expenses_gbp"] == 50.0


def test_yoy_delta():
    mon = datetime.date(2025, 6, 9)
    ly = mon - datetime.timedelta(days=364)
    txs = [
        {"date": mon.isoformat(), "amount": 100, "provider_transaction_id": "c"},
        {"date": ly.isoformat(), "amount": 40, "provider_transaction_id": "d"},
    ]
    r = build_profit_pulse(txs, today=mon + datetime.timedelta(days=2))
    assert r["prior_year_same_week_profit_gbp"] == 40.0
    assert r["yoy_week_profit_delta_gbp"] == 60.0
