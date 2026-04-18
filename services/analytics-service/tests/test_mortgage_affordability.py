import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mortgage_affordability import (
    build_affordability_result,
    monthly_repayment_gbp,
    stamp_duty_england_gbp,
)


def test_monthly_repayment_positive_loan():
    m = monthly_repayment_gbp(200_000, 5.0, 25)
    assert 1100 < m < 1200


def test_stamp_duty_ftb_under_nil_band():
    assert stamp_duty_england_gbp(400_000, first_time_buyer=True, additional_property=False) == 0.0


def test_affordability_max_loan_and_stress():
    r = build_affordability_result(
        annual_income_gbp=50_000,
        employment="self_employed",
        property_price_gbp=300_000,
        deposit_gbp=30_000,
        annual_interest_rate_pct=5.0,
        term_years=30,
        first_time_buyer=False,
        additional_property=False,
    )
    assert r["loan_amount_for_payment_gbp"] == 270_000
    assert r["monthly_payment_if_rates_up_3pp_gbp"] > r["monthly_payment_gbp"]
    assert r["stamp_duty_england_gbp"] is not None
    assert len(r["lender_scenarios"]) >= 3


def test_additional_property_surcharge():
    r = build_affordability_result(
        annual_income_gbp=60_000,
        employment="employed",
        property_price_gbp=350_000,
        deposit_gbp=70_000,
        annual_interest_rate_pct=4.5,
        term_years=30,
        first_time_buyer=False,
        additional_property=True,
    )
    assert r["additional_property_surcharge_applied"] is True
    assert (r["stamp_duty_england_gbp"] or 0) > 0
