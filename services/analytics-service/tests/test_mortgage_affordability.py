import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

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


def test_illustrative_lender_metadata_present():
    r = build_affordability_result(
        annual_income_gbp=60_000,
        employment="self_employed",
        property_price_gbp=300_000,
        deposit_gbp=30_000,
        annual_interest_rate_pct=5.0,
        term_years=25,
        first_time_buyer=True,
        additional_property=False,
    )
    assert r["illustrative_lenders_as_of"]
    assert r["illustrative_lenders_pack_version"] >= 1


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
    assert len(r["lender_scenarios"]) >= 8
    assert "illustrative_fit_score" in r["lender_scenarios"][0]


def test_adverse_credit_prefers_specialist_fit_over_mainstream():
    r = build_affordability_result(
        annual_income_gbp=45_000,
        employment="self_employed",
        property_price_gbp=220_000,
        deposit_gbp=44_000,
        annual_interest_rate_pct=5.5,
        term_years=30,
        first_time_buyer=False,
        additional_property=False,
        credit_band="adverse",
        years_trading=3,
    )
    by_id = {x["id"]: x for x in r["lender_scenarios"]}
    assert by_id["pepper_money"]["illustrative_fit_score"] > by_id["barclays"]["illustrative_fit_score"]


def test_years_trading_validation():
    with pytest.raises(ValueError, match="years_trading"):
        build_affordability_result(
            annual_income_gbp=40_000,
            employment="employed",
            property_price_gbp=None,
            deposit_gbp=None,
            annual_interest_rate_pct=5.0,
            term_years=25,
            first_time_buyer=False,
            additional_property=False,
            years_trading=50,
        )


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


def test_ccj_clean_uses_effective_minor_and_planner_notes():
    r = build_affordability_result(
        annual_income_gbp=48_000,
        employment="self_employed",
        property_price_gbp=200_000,
        deposit_gbp=40_000,
        annual_interest_rate_pct=5.0,
        term_years=30,
        first_time_buyer=False,
        additional_property=False,
        credit_band="clean",
        years_trading=2,
        ccj_in_past_6y=True,
    )
    assert r["credit_band_effective"] == "minor"
    assert r["ccj_in_past_6y"] is True
    assert any("CCJ" in n for n in r["planner_notes"])


def test_buy_to_let_planner_note_and_property_type_echo():
    r = build_affordability_result(
        annual_income_gbp=55_000,
        employment="self_employed",
        property_price_gbp=250_000,
        deposit_gbp=62_500,
        annual_interest_rate_pct=5.0,
        term_years=30,
        first_time_buyer=False,
        additional_property=False,
        property_type="buy_to_let",
    )
    assert r["property_type"] == "buy_to_let"
    assert any("Buy-to-let" in n for n in r["planner_notes"])
