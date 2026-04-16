"""Aligned MTD period summary shape with libs.shared_mtd (same as tax-engine integrations fields)."""

from libs.shared_mtd import build_mtd_self_employment_period_summary


def test_period_summary_matches_hmrc_stub_shape():
    body = build_mtd_self_employment_period_summary(
        period_start_iso="2026-04-06",
        period_end_iso="2026-07-05",
        turnover=10000.0,
        allowable_expenses=1200.0,
    )
    assert body["periodDates"]["periodStartDate"] == "2026-04-06"
    assert body["periodDates"]["periodEndDate"] == "2026-07-05"
    assert body["periodIncome"]["turnover"] == 10000.0
    assert body["periodIncome"]["other"] == 0.0
    assert body["periodExpenses"]["costOfGoods"] == 0.0
    assert body["periodExpenses"]["allowableExpenses"] == 1200.0
