"""
UK Tax Calculators — PAYE, Rental, CIS, Dividend, Crypto, Self-Employed.
Matching Pie.tax's calculator collection for competitive parity.
"""
from typing import Optional
from pydantic import BaseModel

# ── 2025/26 constants ────────────────────────────────────────────────────────
_PA = 12_570.0          # Personal Allowance
_BRT_LIMIT = 37_700.0   # Basic-rate band top (above PA)
_HRT_LIMIT = 125_140.0  # Additional-rate threshold (= PA taper fully withdrawn)
_BRT = 0.20
_HRT = 0.40
_ART = 0.45
_NI_LPL = 12_570.0      # Class 4 Lower Profits Limit
_NI_UPL = 50_270.0      # Class 4 Upper Profits Limit
_NI_C4_MAIN = 0.06      # Class 4 main rate 2025/26
_NI_C4_ADD = 0.02       # Class 4 additional rate
_NI_C2_WEEKLY = 3.45    # Class 2 flat rate / week
_NI_C2_SMALL_PROFITS = 6_725.0   # Small Profits Threshold (Class 2 exemption)
_TRADING_ALLOWANCE = 1_000.0
_DIVIDEND_ALLOWANCE = 500.0
_CGT_EXEMPT = 3_000.0


def _income_tax_bands(taxable_income: float) -> tuple[float, float, float]:
    """Taxable income after PA; bands align with HMRC slices (basic / higher / additional)."""
    basic = min(taxable_income, _BRT_LIMIT) * _BRT
    higher = max(min(taxable_income, _HRT_LIMIT) - _BRT_LIMIT, 0) * _HRT
    additional = max(taxable_income - _HRT_LIMIT, 0) * _ART
    return basic, higher, additional


def _personal_allowance(total_income: float) -> float:
    """PA tapers £1 for every £2 over £100,000."""
    taper_threshold = 100_000.0
    if total_income <= taper_threshold:
        return _PA
    reduction = (total_income - taper_threshold) / 2.0
    return max(_PA - reduction, 0.0)


# ── Self-Employed comprehensive calculator ───────────────────────────────────

class UKSelfEmployedTaxResult(BaseModel):
    gross_trading_income: float
    trading_allowance_used: float
    allowable_expenses_used: float
    net_profit: float
    losses_brought_forward_used: float
    adjusted_profit: float
    personal_allowance: float
    pa_taper_reduction: float
    marriage_allowance_received: float
    taxable_income: float
    basic_rate_tax: float
    higher_rate_tax: float
    additional_rate_tax: float
    total_income_tax: float
    ni_class2: float
    ni_class4_main: float
    ni_class4_additional: float
    total_ni: float
    student_loan_repayment: float
    pension_tax_relief: float
    total_tax_and_ni: float
    payment_on_account_jan: float
    payment_on_account_jul: float
    net_take_home: float
    effective_tax_rate_percent: float


_STUDENT_LOAN_PLANS: dict[str, tuple[float, float]] = {
    "plan1": (24_990.0, 0.09),
    "plan_1": (24_990.0, 0.09),
    "plan2": (27_295.0, 0.09),
    "plan_2": (27_295.0, 0.09),
    "plan4": (31_395.0, 0.09),
    "plan_4": (31_395.0, 0.09),
    "plan5": (25_000.0, 0.09),
    "plan_5": (25_000.0, 0.09),
    "postgrad": (21_000.0, 0.06),
}


def calculate_self_employed_tax(
    gross_trading_income: float,
    allowable_expenses: float = 0.0,
    pension_contributions: float = 0.0,
    student_loan_plan: Optional[str] = None,
    marriage_allowance_received: float = 0.0,
    losses_brought_forward: float = 0.0,
    use_trading_allowance: bool = False,
) -> UKSelfEmployedTaxResult:
    """Full 2025/26 UK self-employed tax calculation."""

    # 1. Net profit
    if use_trading_allowance and allowable_expenses < _TRADING_ALLOWANCE:
        trading_allowance_used = min(gross_trading_income, _TRADING_ALLOWANCE)
        expenses_used = 0.0
    else:
        trading_allowance_used = 0.0
        expenses_used = allowable_expenses

    net_profit = max(gross_trading_income - trading_allowance_used - expenses_used, 0.0)

    # 2. Losses brought forward
    loss_used = min(losses_brought_forward, net_profit)
    adjusted_profit = net_profit - loss_used

    # 3. Pension tax relief (basic rate added back)
    pension_relief = pension_contributions * _BRT

    # 4. Personal allowance (with taper for > £100k)
    total_income_for_pa = adjusted_profit - pension_contributions
    pa = _personal_allowance(total_income_for_pa)
    pa_reduction = _PA - pa
    effective_pa = min(pa + marriage_allowance_received, adjusted_profit)

    # 5. Income tax
    taxable = max(adjusted_profit - pension_contributions - effective_pa, 0.0)
    basic, higher, additional = _income_tax_bands(taxable)
    income_tax = basic + higher + additional

    # 6. Class 2 NI — £0 in-year cash when profits ≥ small profits threshold (treated as paid)
    ni_c2 = 0.0

    # 7. Class 4 NI
    ni_c4_main_base = max(min(adjusted_profit, _NI_UPL) - _NI_LPL, 0.0)
    ni_c4_add_base = max(adjusted_profit - _NI_UPL, 0.0)
    ni_c4_main = ni_c4_main_base * _NI_C4_MAIN
    ni_c4_add = ni_c4_add_base * _NI_C4_ADD
    total_ni = ni_c2 + ni_c4_main + ni_c4_add

    # 8. Student loan
    sl_repayment = 0.0
    sl_key = (student_loan_plan or "").strip().lower().replace("-", "_")
    if sl_key in _STUDENT_LOAN_PLANS:
        threshold, rate = _STUDENT_LOAN_PLANS[sl_key]
        sl_repayment = max(adjusted_profit - threshold, 0.0) * rate

    # 9. Totals
    total_tax_ni = income_tax + total_ni + sl_repayment

    # 10. Payments on Account (each = 50% of prior year tax+NI, due Jan 31 + Jul 31)
    poa = round((income_tax + total_ni) * 0.50, 2)

    net_take_home = gross_trading_income - expenses_used - total_tax_ni
    effective_rate = (total_tax_ni / gross_trading_income * 100) if gross_trading_income > 0 else 0.0

    return UKSelfEmployedTaxResult(
        gross_trading_income=round(gross_trading_income, 2),
        trading_allowance_used=round(trading_allowance_used, 2),
        allowable_expenses_used=round(expenses_used, 2),
        net_profit=round(net_profit, 2),
        losses_brought_forward_used=round(loss_used, 2),
        adjusted_profit=round(adjusted_profit, 2),
        personal_allowance=round(pa, 2),
        pa_taper_reduction=round(pa_reduction, 2),
        marriage_allowance_received=round(marriage_allowance_received, 2),
        taxable_income=round(taxable, 2),
        basic_rate_tax=round(basic, 2),
        higher_rate_tax=round(higher, 2),
        additional_rate_tax=round(additional, 2),
        total_income_tax=round(income_tax, 2),
        ni_class2=round(ni_c2, 2),
        ni_class4_main=round(ni_c4_main, 2),
        ni_class4_additional=round(ni_c4_add, 2),
        total_ni=round(total_ni, 2),
        student_loan_repayment=round(sl_repayment, 2),
        pension_tax_relief=round(pension_relief, 2),
        total_tax_and_ni=round(total_tax_ni, 2),
        payment_on_account_jan=poa,
        payment_on_account_jul=poa,
        net_take_home=round(net_take_home, 2),
        effective_tax_rate_percent=round(effective_rate, 1),
    )


class PAYETaxResult(BaseModel):
    gross_salary: float
    personal_allowance: float
    taxable_income: float
    income_tax: float
    employee_ni: float
    net_pay: float
    effective_rate_percent: float
    monthly_net: float
    weekly_net: float


def calculate_paye(gross_salary: float, tax_code: str = "1257L") -> PAYETaxResult:
    personal_allowance = 12570.0
    taxable = max(gross_salary - personal_allowance, 0)

    tax = 0.0
    remaining = taxable
    basic = min(remaining, 37700)
    tax += basic * 0.20
    remaining -= basic
    higher = min(remaining, 87440) if remaining > 0 else 0
    tax += higher * 0.40
    remaining -= higher
    if remaining > 0:
        tax += remaining * 0.45

    ni = 0.0
    if gross_salary > 12570:
        ni_basic = min(gross_salary - 12570, 50270 - 12570)
        ni += ni_basic * 0.08
        if gross_salary > 50270:
            ni += (gross_salary - 50270) * 0.02

    net = gross_salary - tax - ni
    effective = (tax / gross_salary * 100) if gross_salary > 0 else 0

    return PAYETaxResult(
        gross_salary=gross_salary,
        personal_allowance=personal_allowance,
        taxable_income=taxable,
        income_tax=round(tax, 2),
        employee_ni=round(ni, 2),
        net_pay=round(net, 2),
        effective_rate_percent=round(effective, 1),
        monthly_net=round(net / 12, 2),
        weekly_net=round(net / 52, 2),
    )


class RentalTaxResult(BaseModel):
    rental_income: float
    allowable_expenses: float
    mortgage_interest_relief: float
    taxable_profit: float
    income_tax: float
    ni_class2: float
    total_tax: float
    net_rental_income: float


def calculate_rental_tax(
    rental_income: float,
    mortgage_interest: float = 0,
    repairs: float = 0,
    insurance: float = 0,
    letting_agent_fees: float = 0,
    other_expenses: float = 0,
    other_income: float = 0,
) -> RentalTaxResult:
    expenses = repairs + insurance + letting_agent_fees + other_expenses
    interest_relief = mortgage_interest * 0.20
    taxable = max(rental_income - expenses, 0)
    total_taxable = taxable + other_income

    tax = 0.0
    remaining = max(total_taxable - 12570, 0)
    basic = min(remaining, 37700)
    tax += basic * 0.20
    remaining -= basic
    if remaining > 0:
        higher = min(remaining, 87440)
        tax += higher * 0.40
        remaining -= higher
    if remaining > 0:
        tax += remaining * 0.45

    tax = max(tax - interest_relief, 0)
    ni2 = 0.0

    return RentalTaxResult(
        rental_income=rental_income,
        allowable_expenses=round(expenses, 2),
        mortgage_interest_relief=round(interest_relief, 2),
        taxable_profit=round(taxable, 2),
        income_tax=round(tax, 2),
        ni_class2=ni2,
        total_tax=round(tax + ni2, 2),
        net_rental_income=round(rental_income - expenses - tax - ni2, 2),
    )


class CISTaxResult(BaseModel):
    gross_payment: float
    cis_deduction_rate_percent: float
    cis_deducted: float
    net_payment: float
    materials_cost: float
    taxable_profit: float
    income_tax_due: float
    cis_already_paid: float
    tax_balance: float


def calculate_cis(
    gross_payment: float,
    materials: float = 0,
    cis_rate: float = 20,
    other_expenses: float = 0,
) -> CISTaxResult:
    labour = gross_payment - materials
    cis_deducted = labour * (cis_rate / 100)
    net = gross_payment - cis_deducted
    taxable = max(gross_payment - materials - other_expenses, 0)

    t_inc = max(taxable - 12570, 0)
    tax = min(t_inc, 37700) * 0.20
    tax += max(min(t_inc, 125140) - 37700, 0) * 0.40
    tax += max(t_inc - 125140, 0) * 0.45

    balance = max(tax - cis_deducted, 0)

    return CISTaxResult(
        gross_payment=gross_payment,
        cis_deduction_rate_percent=cis_rate,
        cis_deducted=round(cis_deducted, 2),
        net_payment=round(net, 2),
        materials_cost=materials,
        taxable_profit=round(taxable, 2),
        income_tax_due=round(tax, 2),
        cis_already_paid=round(cis_deducted, 2),
        tax_balance=round(balance, 2),
    )


class DividendTaxResult(BaseModel):
    dividend_income: float
    dividend_allowance: float
    taxable_dividends: float
    basic_rate_tax: float
    higher_rate_tax: float
    additional_rate_tax: float
    total_dividend_tax: float


def calculate_dividend_tax(
    dividend_income: float,
    other_income: float = 0,
    *,
    personal_allowance: Optional[float] = None,
    dividend_allowance: Optional[float] = None,
    basic_band_width: Optional[float] = None,
    higher_band_top: Optional[float] = None,
) -> DividendTaxResult:
    pa = float(personal_allowance) if personal_allowance is not None else _PA
    allowance = float(dividend_allowance) if dividend_allowance is not None else _DIVIDEND_ALLOWANCE
    br_w = float(basic_band_width) if basic_band_width is not None else _BRT_LIMIT
    hr_top = float(higher_band_top) if higher_band_top is not None else _HRT_LIMIT
    taxable = max(dividend_income - allowance, 0)

    total_income = other_income + dividend_income
    income_above_pa = max(total_income - pa, 0)
    non_dividend_above_pa = max(other_income - pa, 0)

    basic_remaining = max(br_w - non_dividend_above_pa, 0)
    basic = min(taxable, basic_remaining)
    basic_tax = basic * 0.0875

    higher_remaining = max(
        (hr_top - br_w) - max(non_dividend_above_pa - br_w, 0) - basic,
        0,
    )
    higher = min(max(taxable - basic, 0), higher_remaining) if taxable > basic else 0
    higher_tax = higher * 0.3375

    additional = max(taxable - basic - higher, 0)
    additional_tax = additional * 0.3935

    return DividendTaxResult(
        dividend_income=dividend_income,
        dividend_allowance=allowance,
        taxable_dividends=round(taxable, 2),
        basic_rate_tax=round(basic_tax, 2),
        higher_rate_tax=round(higher_tax, 2),
        additional_rate_tax=round(additional_tax, 2),
        total_dividend_tax=round(basic_tax + higher_tax + additional_tax, 2),
    )


class CryptoTaxResult(BaseModel):
    total_gains: float
    total_losses: float
    net_gains: float
    annual_exempt_amount: float
    taxable_gains: float
    basic_rate_cgt: float
    higher_rate_cgt: float
    total_cgt: float


def calculate_crypto_tax(
    total_gains: float,
    total_losses: float = 0,
    other_income: float = 0,
    *,
    personal_allowance: Optional[float] = None,
    annual_exempt_amount: Optional[float] = None,
    basic_band_width: Optional[float] = None,
) -> CryptoTaxResult:
    pa = float(personal_allowance) if personal_allowance is not None else _PA
    exempt = float(annual_exempt_amount) if annual_exempt_amount is not None else _CGT_EXEMPT
    br_w = float(basic_band_width) if basic_band_width is not None else _BRT_LIMIT
    net = max(total_gains - total_losses, 0)
    taxable = max(net - exempt, 0)

    income_above_pa = max(other_income - pa, 0)
    basic_remaining = max(br_w - income_above_pa, 0)

    basic = min(taxable, basic_remaining)
    basic_cgt = basic * 0.18
    higher = max(taxable - basic, 0)
    higher_cgt = higher * 0.24

    return CryptoTaxResult(
        total_gains=total_gains,
        total_losses=total_losses,
        net_gains=round(net, 2),
        annual_exempt_amount=exempt,
        taxable_gains=round(taxable, 2),
        basic_rate_cgt=round(basic_cgt, 2),
        higher_rate_cgt=round(higher_cgt, 2),
        total_cgt=round(basic_cgt + higher_cgt, 2),
    )
