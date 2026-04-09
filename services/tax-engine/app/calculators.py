"""
UK Tax Calculators — PAYE, Rental, CIS, Dividend, Crypto.
Matching Pie.tax's calculator collection for competitive parity.
"""
from pydantic import BaseModel


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
    ni2 = 179.40 if taxable > 12570 else 0

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

    tax = 0.0
    remaining = max(taxable - 12570, 0)
    basic = min(remaining, 37700)
    tax += basic * 0.20
    remaining -= basic
    if remaining > 0:
        tax += remaining * 0.40

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
) -> DividendTaxResult:
    allowance = 500.0
    taxable = max(dividend_income - allowance, 0)

    total_income = other_income + dividend_income
    income_above_pa = max(total_income - 12570, 0)
    non_dividend_above_pa = max(other_income - 12570, 0)

    basic_remaining = max(37700 - non_dividend_above_pa, 0)
    basic = min(taxable, basic_remaining)
    basic_tax = basic * 0.0875

    higher_remaining = max(87440 - max(non_dividend_above_pa - 37700, 0) - basic, 0)
    higher = min(max(taxable - basic, 0), higher_remaining) if taxable > basic else 0
    higher_tax = higher * 0.3375

    additional = max(taxable - basic - higher, 0)
    additional_tax = additional * 0.3938

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
) -> CryptoTaxResult:
    exempt = 3000.0
    net = max(total_gains - total_losses, 0)
    taxable = max(net - exempt, 0)

    income_above_pa = max(other_income - 12570, 0)
    basic_remaining = max(37700 - income_above_pa, 0)

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
