import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mortgage_progress_tracker import (
    build_mortgage_progress_timeline,
    merge_backend_signals,
)


def test_first_incomplete_is_current():
    r = build_mortgage_progress_timeline(
        credit_focus="ok",
        deposit_saved_gbp=5_000,
        deposit_target_gbp=50_000,
        monthly_savings_gbp=500,
        debts_priority="managing",
        tax_return_filed=False,
        self_employed_years_override=2.0,
        months_bank_history=None,
        document_count=2,
        mortgage_readiness_percent=30,
    )
    assert r["current_step_id"] == "deposit"
    deposit = next(s for s in r["steps"] if s["id"] == "deposit")
    assert deposit["status"] == "current"
    assert deposit["progress_ratio"] is not None


def test_merge_transactions_fills_months():
    txs = [{"date": "2024-01-15"}, {"date": "2025-12-01"}]
    m = merge_backend_signals(
        {"months_bank_history": None, "document_count": None},
        transactions=txs,
        documents=[{"filename": "a.pdf"}],
    )
    assert m["months_bank_history"] is not None
    assert m["months_bank_history"] >= 20
    assert m["document_count"] == 1


def test_estimated_deposit_months():
    r = build_mortgage_progress_timeline(
        credit_focus="ok",
        deposit_saved_gbp=10_000,
        deposit_target_gbp=40_000,
        monthly_savings_gbp=2_500,
        debts_priority="managing",
        tax_return_filed=True,
        self_employed_years_override=3,
        months_bank_history=30,
        document_count=5,
        mortgage_readiness_percent=80,
    )
    assert r["estimated_months_to_deposit_goal"] == 12
    assert r["estimated_timeline_note"] is not None
