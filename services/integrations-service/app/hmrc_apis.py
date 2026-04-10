"""
HMRC MTD for Income Tax — API integrations for minimum functionality standards.
Ref: https://developer.service.hmrc.gov.uk/guides/income-tax-mtd-end-to-end-service-guide/

These endpoints wrap HMRC sandbox/production APIs. When HMRC credentials are not configured,
they return simulated responses to allow development and testing.
"""
import datetime
import os
import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


HMRC_BASE_URL = os.getenv("HMRC_API_BASE_URL", "https://test-api.service.hmrc.gov.uk")


# === 1. Business Details ===

class BusinessDetail(BaseModel):
    business_id: str
    type_of_business: Literal["self-employment", "uk-property", "foreign-property"]
    trading_name: Optional[str] = None
    accounting_type: Literal["CASH", "ACCRUALS"] = "CASH"
    first_accounting_period_start: Optional[str] = None
    first_accounting_period_end: Optional[str] = None
    accounting_period_start: Optional[str] = None
    accounting_period_end: Optional[str] = None
    ceased: bool = False


def get_business_details_simulated(nino: str) -> list[BusinessDetail]:
    return [
        BusinessDetail(
            business_id=f"XAIS{uuid.uuid4().hex[:8].upper()}",
            type_of_business="self-employment",
            trading_name="Freelance Consulting",
            accounting_type="CASH",
            first_accounting_period_start="2024-04-06",
            first_accounting_period_end="2025-04-05",
            accounting_period_start="2025-04-06",
            accounting_period_end="2026-04-05",
        )
    ]


# === 2. Obligations ===

class Obligation(BaseModel):
    period_start: str
    period_end: str
    due_date: str
    status: Literal["Open", "Fulfilled"]
    received_date: Optional[str] = None


def get_obligations_simulated(nino: str, tax_year: str) -> list[Obligation]:
    year = int(tax_year.split("-")[0]) if "-" in tax_year else int(tax_year)
    return [
        Obligation(period_start=f"{year}-04-06", period_end=f"{year}-07-05", due_date=f"{year}-08-05", status="Fulfilled", received_date=f"{year}-07-28"),
        Obligation(period_start=f"{year}-07-06", period_end=f"{year}-10-05", due_date=f"{year}-11-05", status="Fulfilled", received_date=f"{year}-10-20"),
        Obligation(period_start=f"{year}-10-06", period_end=f"{year+1}-01-05", due_date=f"{year+1}-02-05", status="Open"),
        Obligation(period_start=f"{year+1}-01-06", period_end=f"{year+1}-04-05", due_date=f"{year+1}-05-05", status="Open"),
    ]


# === 3. Self-Employment Business — Periodic Update ===

class PeriodicUpdate(BaseModel):
    period_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    period_start: str
    period_end: str
    turnover: float
    other_income: float = 0.0
    cost_of_goods: float = 0.0
    construction_industry_costs: float = 0.0
    staff_costs: float = 0.0
    travel_costs: float = 0.0
    premises_costs: float = 0.0
    maintenance_costs: float = 0.0
    admin_costs: float = 0.0
    advertising_costs: float = 0.0
    interest: float = 0.0
    financial_charges: float = 0.0
    depreciation: float = 0.0
    professional_fees: float = 0.0
    other_expenses: float = 0.0


class PeriodicUpdateResponse(BaseModel):
    period_id: str
    status: Literal["accepted", "rejected"]
    message: str
    obligation_met: bool


def submit_periodic_update_simulated(update: PeriodicUpdate) -> PeriodicUpdateResponse:
    total_expenses = (
        update.cost_of_goods + update.staff_costs + update.travel_costs +
        update.premises_costs + update.maintenance_costs + update.admin_costs +
        update.advertising_costs + update.interest + update.financial_charges +
        update.professional_fees + update.other_expenses
    )
    return PeriodicUpdateResponse(
        period_id=update.period_id,
        status="accepted",
        message=f"Periodic update accepted. Turnover: \u00a3{update.turnover:.2f}, Expenses: \u00a3{total_expenses:.2f}",
        obligation_met=True,
    )


# === 4. Individual Calculations — Tax Estimate ===

class TaxCalculation(BaseModel):
    calculation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tax_year: str
    total_income: float
    total_deductions: float
    taxable_income: float
    income_tax: float
    national_insurance_class4: float
    national_insurance_class2: float
    total_tax_due: float
    payments_on_account: float = 0.0
    balance_due: float


def calculate_tax_simulated(total_income: float, total_deductions: float, tax_year: str) -> TaxCalculation:
    taxable = max(total_income - total_deductions, 0)

    # Income Tax bands 2025/26
    personal_allowance = 12570.0
    if taxable > 100000:
        personal_allowance = max(0, personal_allowance - (taxable - 100000) / 2)

    income_tax = 0.0
    remaining = max(taxable - personal_allowance, 0)
    basic = min(remaining, 37700)
    income_tax += basic * 0.20
    remaining -= basic
    higher = min(remaining, 87440) if remaining > 0 else 0
    income_tax += higher * 0.40
    remaining -= higher
    if remaining > 0:
        income_tax += remaining * 0.45

    # NI Class 4
    ni4 = 0.0
    if taxable > 12570:
        ni4_basic = min(taxable - 12570, 50270 - 12570)
        ni4 += ni4_basic * 0.06
        if taxable > 50270:
            ni4 += (taxable - 50270) * 0.02

    # NI Class 2
    ni2 = 179.40 if taxable > 12570 else 0.0

    total_tax = round(income_tax + ni4 + ni2, 2)

    return TaxCalculation(
        tax_year=tax_year,
        total_income=total_income,
        total_deductions=total_deductions,
        taxable_income=taxable,
        income_tax=round(income_tax, 2),
        national_insurance_class4=round(ni4, 2),
        national_insurance_class2=ni2,
        total_tax_due=total_tax,
        balance_due=total_tax,
    )


# === 5. Individual Losses ===

class LossRecord(BaseModel):
    loss_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tax_year: str
    type_of_loss: Literal["self-employment", "uk-property", "foreign-property"]
    loss_amount: float
    remaining_amount: float
    relief_type: Literal["carry-forward", "carry-sideways", "carry-back"]
    status: Literal["active", "fully-relieved"]


_losses_store: list[dict] = []

def record_loss_simulated(tax_year: str, loss_type: str, amount: float, relief: str) -> LossRecord:
    record = LossRecord(
        tax_year=tax_year,
        type_of_loss=loss_type,
        loss_amount=amount,
        remaining_amount=amount,
        relief_type=relief,
        status="active",
    )
    _losses_store.append(record.model_dump())
    return record

def get_losses_simulated(tax_year: str) -> list[LossRecord]:
    return [LossRecord(**l) for l in _losses_store if l["tax_year"] == tax_year]


# === 6. VAT Return ===

class VATReturn(BaseModel):
    period_key: str
    vat_due_sales: float
    vat_due_acquisitions: float = 0.0
    total_vat_due: float
    vat_reclaimed: float
    net_vat_due: float
    total_value_sales: float
    total_value_purchases: float
    total_value_goods_supplied: float = 0.0
    total_acquisitions: float = 0.0

class VATReturnResponse(BaseModel):
    processing_date: str
    form_bundle_number: str
    payment_indicator: Literal["DD", "BANK", "DIRECT DEBIT"]
    charge_ref_number: str
    status: Literal["accepted", "rejected"]

def submit_vat_return_simulated(vat_return: VATReturn) -> VATReturnResponse:
    return VATReturnResponse(
        processing_date=datetime.datetime.now(datetime.UTC).isoformat(),
        form_bundle_number=f"VAT-{uuid.uuid4().hex[:12].upper()}",
        payment_indicator="DD",
        charge_ref_number=f"VATC-{uuid.uuid4().hex[:8].upper()}",
        status="accepted",
    )


class VATObligation(BaseModel):
    period_key: str
    start: str
    end: str
    due: str
    status: Literal["O", "F"]  # O=Open, F=Fulfilled
    received: Optional[str] = None

def get_vat_obligations_simulated(vrn: str) -> list[VATObligation]:
    now = datetime.datetime.now(datetime.UTC)
    year = now.year
    return [
        VATObligation(period_key=f"{year}Q1", start=f"{year}-01-01", end=f"{year}-03-31", due=f"{year}-05-07", status="F", received=f"{year}-04-28"),
        VATObligation(period_key=f"{year}Q2", start=f"{year}-04-01", end=f"{year}-06-30", due=f"{year}-08-07", status="O"),
        VATObligation(period_key=f"{year}Q3", start=f"{year}-07-01", end=f"{year}-09-30", due=f"{year}-11-07", status="O"),
        VATObligation(period_key=f"{year}Q4", start=f"{year}-10-01", end=f"{year}-12-31", due=f"{year+1}-02-07", status="O"),
    ]
