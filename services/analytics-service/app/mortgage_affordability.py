"""
Illustrative UK mortgage affordability, repayment, stress, and SDLT (England).

Figures are for planning only — not a mortgage offer, underwriting decision, or tax advice.
Verify SDLT and lender rules against gov.uk and current lender criteria before acting.
"""

from __future__ import annotations

from typing import Any, Literal

EmploymentKind = Literal["employed", "self_employed"]
CreditBand = Literal["clean", "minor", "adverse"]

# Income multiples (illustrative planning bands — lender policy varies).
EMPLOYED_INCOME_MULTIPLE = 4.5
SELF_EMPLOYED_INCOME_MULTIPLE_LOW = 3.0
SELF_EMPLOYED_INCOME_MULTIPLE_HIGH = 4.0
SELF_EMPLOYED_INCOME_MULTIPLE_MID = 3.5

STRESS_RATE_ADD_PCT_POINTS = 3.0

NAMED_LENDER_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "barclays",
        "label": "Barclays-style (illustrative)",
        "min_accounts_years": 1,
        "income_multiple": 4.49,
        "min_deposit_pct": 10,
        "notes": "Often cited minimum history ~1 year for some self-employed cases; policy varies.",
    },
    {
        "id": "hsbc",
        "label": "HSBC-style (illustrative)",
        "min_accounts_years": 2,
        "income_multiple": 4.0,
        "min_deposit_pct": 10,
        "segment": "mainstream",
        "notes": "Typically expects ~2 years accounts for self-employed income.",
    },
    {
        "id": "halifax",
        "label": "Halifax-style (illustrative)",
        "min_accounts_years": 2,
        "income_multiple": 4.0,
        "min_deposit_pct": 10,
        "segment": "mainstream",
        "notes": "May consider retained profit for limited company directors — underwriting dependent.",
    },
    {
        "id": "nationwide",
        "label": "Nationwide-style (illustrative)",
        "min_accounts_years": 2,
        "income_multiple": 4.5,
        "min_deposit_pct": 10,
        "notes": "Strong applications sometimes quoted toward upper multiple ranges.",
    },
    {
        "id": "natwest",
        "label": "NatWest-style (illustrative)",
        "min_accounts_years": 2,
        "income_multiple": 4.0,
        "min_deposit_pct": 10,
        "segment": "mainstream",
        "notes": "Contractor / complex income may be flex-underwritten — case by case.",
    },
    {
        "id": "kensington",
        "label": "Kensington-style (illustrative specialist)",
        "min_accounts_years": 2,
        "income_multiple": 3.75,
        "min_deposit_pct": 15,
        "segment": "specialist",
        "notes": "Near-prime specialist; impaired credit sometimes considered with larger deposit; pricing reflects risk.",
    },
    {
        "id": "pepper_money",
        "label": "Pepper Money-style (illustrative specialist)",
        "min_accounts_years": 2,
        "income_multiple": 3.5,
        "min_deposit_pct": 20,
        "segment": "specialist",
        "notes": "Specialist lender; complex income or credit history — underwriting varies by case.",
    },
    {
        "id": "together",
        "label": "Together-style (illustrative specialist)",
        "min_accounts_years": 1,
        "income_multiple": 3.25,
        "min_deposit_pct": 25,
        "segment": "specialist",
        "notes": "Specialist / short-term secured products; higher deposits common — confirm product suitability.",
    },
]


def _illustrative_fit_score(
    row: dict[str, Any],
    *,
    credit_band: CreditBand,
    years_trading: int | None,
    deposit_pct: float | None,
) -> tuple[float, list[str]]:
    """Heuristic 0–100 score for ordering scenarios only — not an approval probability."""
    reasons: list[str] = []
    segment = str(row.get("segment") or "mainstream")
    is_specialist = segment == "specialist"
    score = 68.0

    if credit_band == "clean":
        score += 6
        if is_specialist:
            score -= 4
            reasons.append("Clean credit: high-street lenders often competitive on pricing.")
    elif credit_band == "minor":
        score -= 4
        if is_specialist:
            score += 14
            reasons.append("Minor credit issues: specialists sometimes more flexible.")
        else:
            score -= 6
            reasons.append("Minor credit: some mainstream lenders may still consider — case by case.")
    else:
        if is_specialist:
            score += 24
            reasons.append("Adverse credit: illustrative tilt toward specialist segment (not a guarantee).")
        else:
            score -= 32
            reasons.append("Adverse credit: many high-street scenarios become difficult — seek broker advice.")

    if years_trading is not None:
        need = int(row["min_accounts_years"])
        if years_trading < need:
            score -= 16
            reasons.append(f"Accounts history: scenario often cites ~{need}y; you entered {years_trading}y.")
        else:
            score += 7

    if deposit_pct is not None:
        need_dep = int(row["min_deposit_pct"])
        if deposit_pct + 0.01 >= need_dep:
            score += 8
            reasons.append(f"Deposit meets illustrative {need_dep}% minimum for this scenario.")
        else:
            gap = need_dep - deposit_pct
            score -= min(28.0, gap * 2.8)
            reasons.append(
                f"Deposit below illustrative {need_dep}% for this scenario (you have ~{deposit_pct:.1f}%)."
            )

    score = max(0.0, min(100.0, score))
    return round(score, 1), reasons


def monthly_repayment_gbp(loan_gbp: float, annual_interest_rate_pct: float, term_years: int) -> float:
    """Capital-and-interest repayment; monthly instalment."""
    if loan_gbp <= 0:
        return 0.0
    months = max(1, int(term_years) * 12)
    monthly_rate = (annual_interest_rate_pct / 100.0) / 12.0
    if monthly_rate <= 0:
        return round(loan_gbp / months, 2)
    factor = (1 + monthly_rate) ** months
    payment = loan_gbp * monthly_rate * factor / (factor - 1)
    return round(payment, 2)


def _sdlt_standard_england(price: float) -> float:
    """Residential SDLT — main rates (England), marginal slices (verify gov.uk)."""
    if price <= 0:
        return 0.0
    tax = 0.0
    prev = 0.0
    bands: list[tuple[float, float]] = [
        (250_000, 0.0),
        (925_000, 0.05),
        (1_500_000, 0.10),
        (float("inf"), 0.12),
    ]
    for top, rate in bands:
        if price <= prev:
            break
        slice_end = min(price, top)
        tax += (slice_end - prev) * rate
        prev = slice_end
    return round(tax, 2)


def stamp_duty_england_gbp(
    price: float,
    *,
    first_time_buyer: bool,
    additional_property: bool,
) -> float:
    if price <= 0:
        return 0.0
    if first_time_buyer and price <= 625_000:
        if price <= 425_000:
            base = 0.0
        else:
            base = round((price - 425_000) * 0.05, 2)
    else:
        base = _sdlt_standard_england(price)
    if additional_property and price > 40_000:
        base += round(price * 0.03, 2)
    return round(base, 2)


def _baseline_multiple(employment: EmploymentKind) -> float:
    if employment == "employed":
        return EMPLOYED_INCOME_MULTIPLE
    return SELF_EMPLOYED_INCOME_MULTIPLE_MID


def build_affordability_result(
    *,
    annual_income_gbp: float,
    employment: EmploymentKind,
    property_price_gbp: float | None,
    deposit_gbp: float | None,
    annual_interest_rate_pct: float,
    term_years: int,
    first_time_buyer: bool,
    additional_property: bool,
    credit_band: CreditBand = "clean",
    years_trading: int | None = None,
) -> dict[str, Any]:
    if annual_income_gbp <= 0:
        raise ValueError("annual_income_gbp must be positive")
    if annual_interest_rate_pct < 0 or annual_interest_rate_pct > 25:
        raise ValueError("annual_interest_rate_pct out of supported range")
    if term_years < 5 or term_years > 40:
        raise ValueError("term_years must be between 5 and 40")
    if property_price_gbp is not None and property_price_gbp < 0:
        raise ValueError("property_price_gbp cannot be negative")
    if deposit_gbp is not None and deposit_gbp < 0:
        raise ValueError("deposit_gbp cannot be negative")
    if years_trading is not None and (years_trading < 0 or years_trading > 40):
        raise ValueError("years_trading must be between 0 and 40")

    deposit_pct: float | None = None
    if (
        property_price_gbp
        and property_price_gbp > 0
        and deposit_gbp is not None
        and deposit_gbp >= 0
    ):
        deposit_pct = round(100.0 * deposit_gbp / property_price_gbp, 2)

    baseline = _baseline_multiple(employment)
    max_from_income = round(annual_income_gbp * baseline, 2)
    max_from_income_low = round(annual_income_gbp * SELF_EMPLOYED_INCOME_MULTIPLE_LOW, 2)
    max_from_income_high = round(annual_income_gbp * SELF_EMPLOYED_INCOME_MULTIPLE_HIGH, 2)

    loan_for_payment: float | None = None
    ltv_pct: float | None = None
    if property_price_gbp and property_price_gbp > 0 and deposit_gbp is not None:
        loan_for_payment = max(0.0, round(property_price_gbp - deposit_gbp, 2))
        if loan_for_payment > property_price_gbp:
            loan_for_payment = property_price_gbp
        ltv_pct = round(100.0 * loan_for_payment / property_price_gbp, 2) if property_price_gbp else None
    elif max_from_income > 0:
        loan_for_payment = max_from_income

    pay_monthly = (
        monthly_repayment_gbp(loan_for_payment, annual_interest_rate_pct, term_years)
        if loan_for_payment
        else 0.0
    )
    stressed_rate = annual_interest_rate_pct + STRESS_RATE_ADD_PCT_POINTS
    pay_stressed = (
        monthly_repayment_gbp(loan_for_payment, stressed_rate, term_years)
        if loan_for_payment
        else 0.0
    )

    sdlt = (
        stamp_duty_england_gbp(property_price_gbp, first_time_buyer=first_time_buyer, additional_property=additional_property)
        if property_price_gbp and property_price_gbp > 0
        else None
    )

    lender_rows: list[dict[str, Any]] = []
    for row in NAMED_LENDER_SCENARIOS:
        mult = float(row["income_multiple"])
        cap = round(annual_income_gbp * mult, 2)
        fit, fit_reasons = _illustrative_fit_score(
            row,
            credit_band=credit_band,
            years_trading=years_trading,
            deposit_pct=deposit_pct,
        )
        lender_rows.append(
            {
                **row,
                "max_loan_from_income_gbp": cap,
                "illustrative_fit_score": fit,
                "illustrative_fit_reasons": fit_reasons,
            }
        )
    lender_rows.sort(key=lambda x: float(x["illustrative_fit_score"]), reverse=True)

    disclaimer = (
        "Illustrative numbers only — not a mortgage offer, affordability assessment, or regulated advice. "
        "Lenders apply stress tests, credit scoring, and expenditure checks. "
        "Lender ordering uses a heuristic fit score from credit band, deposit %, and trading history — not approval odds. "
        "SDLT is modelled for England using simplified bands; confirm with gov.uk / your conveyancer."
    )

    return {
        "employment": employment,
        "credit_band": credit_band,
        "years_trading": years_trading,
        "deposit_pct_computed": deposit_pct,
        "baseline_income_multiple": baseline,
        "employed_planning_multiple": EMPLOYED_INCOME_MULTIPLE,
        "self_employed_planning_multiple_range": [
            float(SELF_EMPLOYED_INCOME_MULTIPLE_LOW),
            float(SELF_EMPLOYED_INCOME_MULTIPLE_HIGH),
        ],
        "max_loan_from_income_gbp": max_from_income,
        "max_loan_from_income_gbp_self_employed_range": (
            [max_from_income_low, max_from_income_high] if employment == "self_employed" else None
        ),
        "loan_amount_for_payment_gbp": loan_for_payment,
        "ltv_pct": ltv_pct,
        "monthly_payment_gbp": pay_monthly,
        "annual_interest_rate_pct": round(annual_interest_rate_pct, 4),
        "stressed_annual_interest_rate_pct": round(stressed_rate, 4),
        "stress_rate_add_pct_points": STRESS_RATE_ADD_PCT_POINTS,
        "monthly_payment_if_rates_up_3pp_gbp": pay_stressed,
        "stamp_duty_england_gbp": sdlt,
        "first_time_buyer": first_time_buyer,
        "additional_property_surcharge_applied": bool(additional_property and (property_price_gbp or 0) > 40_000),
        "term_years": term_years,
        "lender_scenarios": lender_rows,
        "disclaimer": disclaimer,
    }
