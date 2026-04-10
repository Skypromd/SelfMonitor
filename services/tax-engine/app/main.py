import datetime
import logging
import os
import sys
import json
from pathlib import Path
from typing import Any, List, Optional, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)

# --- Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/transactions/me")
INTEGRATIONS_SERVICE_URL = os.getenv("INTEGRATIONS_SERVICE_URL", "http://localhost:8010/integrations/hmrc/submit-tax-return")
MTD_QUARTERLY_INTEGRATIONS_SERVICE_URL = os.getenv(
    "MTD_QUARTERLY_INTEGRATIONS_SERVICE_URL",
    "http://localhost:8010/integrations/hmrc/mtd/quarterly-update",
)
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8015/events")
INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://invoice-service:80")
DEDUCTIBLE_EXPENSE_CATEGORIES = {"transport", "subscriptions", "office_supplies"}
UK_PERSONAL_ALLOWANCE = 12570.0
UK_BASIC_TAX_RATE = 0.20
UK_CLASS4_NIC_LOWER_PROFITS_LIMIT = 12570.0
UK_CLASS4_NIC_MAIN_RATE_UPPER_LIMIT = 50270.0
UK_CLASS4_NIC_MAIN_RATE = 0.06
UK_CLASS4_NIC_ADDITIONAL_RATE = 0.02
DEFAULT_MTD_ITSA_RULES: list[dict[str, Any]] = [
    {
        "policy_code": "UK_MTD_ITSA_2026",
        "effective_from": "2026-04-06",
        "threshold": 50000.0,
        "reporting_cadence": "quarterly_updates_plus_final_declaration",
    },
    {
        "policy_code": "UK_MTD_ITSA_2027",
        "effective_from": "2027-04-06",
        "threshold": 30000.0,
        "reporting_cadence": "quarterly_updates_plus_final_declaration",
    },
    {
        "policy_code": "UK_MTD_ITSA_2028",
        "effective_from": "2028-04-06",
        "threshold": 20000.0,
        "reporting_cadence": "quarterly_updates_plus_final_declaration",
    },
]
MTD_ITSA_RULES_ENV = os.getenv("TAX_MTD_ITSA_RULES_JSON")
TAX_CALCULATIONS_TOTAL = Counter(
    "tax_calculations_total",
    "Total tax calculation attempts grouped by result.",
    labelnames=("result",),
)
TAX_SUBMISSIONS_TOTAL = Counter(
    "tax_submissions_total",
    "Total tax submission attempts grouped by result.",
    labelnames=("result",),
)

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_http.retry import get_json_with_retry, post_json_with_retry

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Tax Engine Service",
    description="Calculates tax liabilities based on categorized transactions.",
    version="1.0.0"
)

# Instrument the app for OpenTelemetry
setup_telemetry(app)

# --- Models ---
class Transaction(BaseModel):
    date: datetime.date
    amount: float
    category: Optional[str] = None

class TaxCalculationRequest(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    jurisdiction: str

class TaxSummaryItem(BaseModel):
    category: str
    total_amount: float
    taxable_amount: float

class TaxCalculationResult(BaseModel):
    user_id: str
    start_date: datetime.date
    end_date: datetime.date
    total_income: float
    total_expenses: float
    taxable_profit: float
    personal_allowance_used: float
    taxable_amount_after_allowance: float
    estimated_income_tax_due: float
    estimated_class4_nic_due: float
    estimated_effective_tax_rate: float
    estimated_tax_due: float
    mtd_obligation: dict[str, Any]
    summary_by_category: List[TaxSummaryItem]


def _parse_iso_date(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return datetime.date.fromisoformat(stripped)
        except ValueError:
            return None
    return None


def _load_mtd_itsa_rules() -> list[dict[str, Any]]:
    if not MTD_ITSA_RULES_ENV:
        return list(DEFAULT_MTD_ITSA_RULES)
    try:
        payload = json.loads(MTD_ITSA_RULES_ENV)
    except json.JSONDecodeError:
        return list(DEFAULT_MTD_ITSA_RULES)
    if not isinstance(payload, list):
        return list(DEFAULT_MTD_ITSA_RULES)

    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        policy_code = str(item.get("policy_code") or "").strip()
        effective_from = _parse_iso_date(item.get("effective_from"))
        threshold_value = item.get("threshold")
        cadence = str(item.get("reporting_cadence") or "").strip()
        if not policy_code or effective_from is None or cadence != "quarterly_updates_plus_final_declaration":
            continue
        try:
            threshold = float(threshold_value)
        except (TypeError, ValueError):
            continue
        if threshold <= 0:
            continue
        normalized.append(
            {
                "policy_code": policy_code,
                "effective_from": effective_from.isoformat(),
                "threshold": threshold,
                "reporting_cadence": cadence,
            }
        )
    return normalized if normalized else list(DEFAULT_MTD_ITSA_RULES)


def _uk_tax_year_bounds(reference_date: datetime.date) -> tuple[datetime.date, datetime.date]:
    if (reference_date.month, reference_date.day) >= (4, 6):
        start_year = reference_date.year
    else:
        start_year = reference_date.year - 1
    tax_year_start = datetime.date(start_year, 4, 6)
    tax_year_end = datetime.date(start_year + 1, 4, 5)
    return tax_year_start, tax_year_end


def _next_month_same_day(date_value: datetime.date) -> datetime.date:
    if date_value.month == 12:
        return datetime.date(date_value.year + 1, 1, date_value.day)
    return datetime.date(date_value.year, date_value.month + 1, date_value.day)


def _resolve_active_mtd_rule(tax_year_start: datetime.date) -> dict[str, Any] | None:
    rules = _load_mtd_itsa_rules()
    active_rule: dict[str, Any] | None = None
    for rule in rules:
        effective_from = _parse_iso_date(rule.get("effective_from"))
        if effective_from is None:
            continue
        if effective_from <= tax_year_start:
            if active_rule is None:
                active_rule = rule
                continue
            previous_effective = _parse_iso_date(active_rule.get("effective_from"))
            if previous_effective is None or effective_from > previous_effective:
                active_rule = rule
    return active_rule


def _build_quarterly_windows(
    tax_year_start: datetime.date,
    *,
    today: datetime.date,
) -> list[dict[str, str]]:
    year = tax_year_start.year
    quarter_rows = [
        ("Q1", datetime.date(year, 4, 6), datetime.date(year, 7, 5)),
        ("Q2", datetime.date(year, 7, 6), datetime.date(year, 10, 5)),
        ("Q3", datetime.date(year, 10, 6), datetime.date(year + 1, 1, 5)),
        ("Q4", datetime.date(year + 1, 1, 6), datetime.date(year + 1, 4, 5)),
    ]
    result: list[dict[str, str]] = []
    for label, period_start, period_end in quarter_rows:
        due_date = _next_month_same_day(period_end)
        if today > due_date:
            status_value = "overdue"
        elif today >= period_end:
            status_value = "due_now"
        else:
            status_value = "upcoming"
        result.append(
            {
                "quarter": label,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "due_date": due_date.isoformat(),
                "status": status_value,
            }
        )
    return result


def _build_mtd_obligation(
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    total_income: float,
    today: datetime.date,
) -> dict[str, Any]:
    tax_year_start, tax_year_end = _uk_tax_year_bounds(period_end)
    active_rule = _resolve_active_mtd_rule(tax_year_start)
    period_days = max((period_end - period_start).days + 1, 1)
    annualized_income_estimate = round((total_income * 365.0) / period_days, 2)
    notes: list[str] = []
    if period_days < 330:
        notes.append(
            "MTD threshold assessment is annualized because the selected period is shorter than a full tax year."
        )
    else:
        notes.append("MTD threshold assessment uses selected period income totals.")

    if active_rule is None:
        notes.append("No quarterly MTD ITSA policy is active for the selected tax year.")
        return {
            "tax_year_start": tax_year_start.isoformat(),
            "tax_year_end": tax_year_end.isoformat(),
            "policy_code": "UK_SELF_ASSESSMENT_ANNUAL_ONLY",
            "threshold": None,
            "qualifying_income_estimate": annualized_income_estimate,
            "reporting_required": False,
            "reporting_cadence": "annual_only",
            "quarterly_updates": [],
            "final_declaration_required": True,
            "next_deadline": None,
            "notes": notes,
        }

    threshold = float(active_rule.get("threshold") or 0.0)
    reporting_required = annualized_income_estimate > threshold
    quarterly_updates = (
        _build_quarterly_windows(tax_year_start, today=today)
        if reporting_required
        else []
    )
    next_deadline = None
    for row in quarterly_updates:
        due_date = _parse_iso_date(row.get("due_date"))
        if due_date is None:
            continue
        if due_date >= today:
            next_deadline = due_date.isoformat()
            break
    if reporting_required:
        notes.append(
            f"Estimated qualifying income {annualized_income_estimate:.2f} exceeds active threshold {threshold:.2f}."
        )
    else:
        notes.append(
            f"Estimated qualifying income {annualized_income_estimate:.2f} does not exceed active threshold {threshold:.2f}."
        )

    return {
        "tax_year_start": tax_year_start.isoformat(),
        "tax_year_end": tax_year_end.isoformat(),
        "policy_code": str(active_rule.get("policy_code") or "UK_MTD_ITSA"),
        "threshold": threshold,
        "qualifying_income_estimate": annualized_income_estimate,
        "reporting_required": reporting_required,
        "reporting_cadence": (
            "quarterly_updates_plus_final_declaration"
            if reporting_required
            else "annual_only"
        ),
        "quarterly_updates": quarterly_updates,
        "final_declaration_required": True,
        "next_deadline": next_deadline,
        "notes": notes,
    }


def _resolve_matching_mtd_quarter(
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    mtd_obligation: dict[str, Any],
) -> dict[str, Any] | None:
    quarterly_updates = mtd_obligation.get("quarterly_updates")
    if not isinstance(quarterly_updates, list):
        return None
    for quarter in quarterly_updates:
        if not isinstance(quarter, dict):
            continue
        quarter_start = _parse_iso_date(quarter.get("period_start"))
        quarter_end = _parse_iso_date(quarter.get("period_end"))
        if quarter_start == period_start and quarter_end == period_end:
            return quarter
    return None


def _is_full_mtd_tax_year_submission(
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    mtd_obligation: dict[str, Any],
) -> bool:
    tax_year_start = _parse_iso_date(mtd_obligation.get("tax_year_start"))
    tax_year_end = _parse_iso_date(mtd_obligation.get("tax_year_end"))
    return tax_year_start == period_start and tax_year_end == period_end


def _build_mtd_quarterly_submission_payload(
    *,
    user_id: str,
    request: "TaxCalculationRequest",
    calculation_result: "TaxCalculationResult",
    mtd_obligation: dict[str, Any],
    quarter_window: dict[str, Any],
) -> dict[str, Any]:
    category_summary = [
        item.model_dump() for item in calculation_result.summary_by_category
    ]
    return {
        "submission_channel": "api",
        "correlation_id": f"tax-engine-{user_id}-{request.start_date.isoformat()}-{request.end_date.isoformat()}",
        "report": {
            "schema_version": "hmrc-mtd-itsa-quarterly-v1",
            "jurisdiction": "UK",
            "policy_code": str(mtd_obligation.get("policy_code") or "UK_MTD_ITSA"),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "business": {
                "taxpayer_ref": user_id,
                "business_name": f"Sole trader account {user_id}",
                "accounting_method": "cash",
            },
            "period": {
                "tax_year_start": str(mtd_obligation.get("tax_year_start")),
                "tax_year_end": str(mtd_obligation.get("tax_year_end")),
                "quarter": str(quarter_window.get("quarter")),
                "period_start": request.start_date.isoformat(),
                "period_end": request.end_date.isoformat(),
                "due_date": str(quarter_window.get("due_date")),
            },
            "financials": {
                "turnover": round(calculation_result.total_income, 2),
                "allowable_expenses": round(calculation_result.total_expenses, 2),
                "taxable_profit": round(calculation_result.taxable_profit, 2),
                "estimated_tax_due": round(calculation_result.estimated_tax_due, 2),
                "currency": "GBP",
            },
            "category_summary": category_summary,
            "declaration": "true_and_complete",
        },
    }


def _calculate_class4_nic(taxable_profit: float) -> float:
    if taxable_profit <= UK_CLASS4_NIC_LOWER_PROFITS_LIMIT:
        return 0.0
    main_band_taxable = max(
        min(taxable_profit, UK_CLASS4_NIC_MAIN_RATE_UPPER_LIMIT) - UK_CLASS4_NIC_LOWER_PROFITS_LIMIT,
        0.0,
    )
    additional_band_taxable = max(taxable_profit - UK_CLASS4_NIC_MAIN_RATE_UPPER_LIMIT, 0.0)
    return (main_band_taxable * UK_CLASS4_NIC_MAIN_RATE) + (
        additional_band_taxable * UK_CLASS4_NIC_ADDITIONAL_RATE
    )

# --- Endpoints ---
@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/calculate", response_model=TaxCalculationResult)
async def calculate_tax(
    request: TaxCalculationRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    if request.start_date > request.end_date:
        TAX_CALCULATIONS_TOTAL.labels(result="validation_error").inc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date cannot be before start date.")
    if request.jurisdiction != "UK":
        TAX_CALCULATIONS_TOTAL.labels(result="validation_error").inc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'UK' jurisdiction is supported.")

    # 1. Fetch all transactions for the user from the transactions-service
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        transactions_data = await get_json_with_retry(
            TRANSACTIONS_SERVICE_URL,
            headers=headers,
            timeout=10.0,
        )
        transactions = [Transaction(**t) for t in transactions_data]
    except httpx.HTTPError as exc:
        TAX_CALCULATIONS_TOTAL.labels(result="upstream_error").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not connect to transactions-service: {exc}",
        ) from exc

    # 2. Filter transactions by date and calculate totals
    total_income = 0.0
    total_expenses = 0.0
    summary_map = {}

    for t in transactions:
        if request.start_date <= t.date <= request.end_date:
            if t.amount > 0:
                total_income += t.amount
            elif t.category in DEDUCTIBLE_EXPENSE_CATEGORIES:
                total_expenses += abs(t.amount)

            category = t.category or "uncategorized"
            summary_map.setdefault(category, 0.0)
            summary_map[category] += t.amount

    # 3. Apply simplified UK tax rules
    taxable_profit = max(total_income - total_expenses, 0.0)
    personal_allowance_used = min(taxable_profit, UK_PERSONAL_ALLOWANCE)
    taxable_amount_after_allowance = max(0, taxable_profit - UK_PERSONAL_ALLOWANCE)
    estimated_income_tax = taxable_amount_after_allowance * UK_BASIC_TAX_RATE
    estimated_class4_nic = _calculate_class4_nic(taxable_profit)
    estimated_tax = estimated_income_tax + estimated_class4_nic
    effective_tax_rate = (estimated_tax / taxable_profit) if taxable_profit > 0 else 0.0

    # 4. Prepare summary
    summary_by_category = [
        TaxSummaryItem(category=cat, total_amount=round(amount, 2), taxable_amount=round(amount, 2)) # Simplified
        for cat, amount in summary_map.items()
    ]

    mtd_obligation = _build_mtd_obligation(
        period_start=request.start_date,
        period_end=request.end_date,
        total_income=total_income,
        today=datetime.date.today(),
    )
    TAX_CALCULATIONS_TOTAL.labels(result="success").inc()
    return TaxCalculationResult(
        user_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        taxable_profit=round(taxable_profit, 2),
        personal_allowance_used=round(personal_allowance_used, 2),
        taxable_amount_after_allowance=round(taxable_amount_after_allowance, 2),
        estimated_income_tax_due=round(estimated_income_tax, 2),
        estimated_class4_nic_due=round(estimated_class4_nic, 2),
        estimated_effective_tax_rate=round(effective_tax_rate, 4),
        estimated_tax_due=round(estimated_tax, 2),
        mtd_obligation=mtd_obligation,
        summary_by_category=summary_by_category,
    )

@app.post("/calculate-and-submit", status_code=status.HTTP_202_ACCEPTED)
async def calculate_and_submit_tax(
    request: TaxCalculationRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    # This re-uses the logic from the calculate endpoint.
    # In a real app, this logic would be in a shared function.
    calculation_result = await calculate_tax(request, user_id, bearer_token)

    # 5. Submit the calculated tax to the integrations service.
    # For compliant MTD quarterly windows we use a dedicated direct HMRC endpoint.
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        mtd_obligation = (
            calculation_result.mtd_obligation
            if isinstance(calculation_result.mtd_obligation, dict)
            else {}
        )
        submission_payload: dict[str, Any]
        submission_url = INTEGRATIONS_SERVICE_URL
        submission_mode = "annual_tax_return"
        is_mtd_reporting = bool(mtd_obligation.get("reporting_required"))
        quarter_window = _resolve_matching_mtd_quarter(
            period_start=request.start_date,
            period_end=request.end_date,
            mtd_obligation=mtd_obligation,
        )
        if is_mtd_reporting and quarter_window is not None:
            submission_payload = _build_mtd_quarterly_submission_payload(
                user_id=user_id,
                request=request,
                calculation_result=calculation_result,
                mtd_obligation=mtd_obligation,
                quarter_window=quarter_window,
            )
            submission_url = MTD_QUARTERLY_INTEGRATIONS_SERVICE_URL
            submission_mode = "mtd_quarterly_update"
        else:
            if is_mtd_reporting and not _is_full_mtd_tax_year_submission(
                period_start=request.start_date,
                period_end=request.end_date,
                mtd_obligation=mtd_obligation,
            ):
                TAX_SUBMISSIONS_TOTAL.labels(result="validation_error").inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "For MTD quarterly reporting, submission period must match an HMRC quarter "
                        "or the full tax year for final declaration."
                    ),
                )
            submission_payload = {
                "tax_period_start": request.start_date.isoformat(),
                "tax_period_end": request.end_date.isoformat(),
                "tax_due": calculation_result.estimated_tax_due,
            }
        submission_data = await post_json_with_retry(
            submission_url,
            headers=headers,
            json_body=submission_payload,
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        TAX_SUBMISSIONS_TOTAL.labels(result="upstream_error").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not connect to integrations-service: {exc}",
        ) from exc

    # 6. Create a calendar event for the payment deadline
    try:
        # UK Self Assessment payment deadline is 31st Jan of the next year
        deadline_year = request.end_date.year + 1
        deadline = datetime.date(deadline_year, 1, 31)
        await post_json_with_retry(
            CALENDAR_SERVICE_URL,
            json_body={
                "user_id": user_id,
                "event_title": "UK Self Assessment Tax Payment Due",
                "event_date": deadline.isoformat(),
                "notes": (
                    f"Estimated tax due: £{calculation_result.estimated_tax_due}. "
                    f"Submission ID: {submission_data.get('submission_id')}"
                ),
            },
            expect_json=False,
        )
    except httpx.HTTPError:
        # This is a non-critical step, so we don't fail the whole request if it fails.
        logger.warning("Could not create calendar event.")

    # 7. Create quarterly MTD reminder events when quarterly updates are required.
    if bool(mtd_obligation.get("reporting_required")):
        quarterly_updates = mtd_obligation.get("quarterly_updates")
        if isinstance(quarterly_updates, list):
            for quarter in quarterly_updates:
                if not isinstance(quarter, dict):
                    continue
                quarter_label = str(quarter.get("quarter") or "").strip()
                due_date = str(quarter.get("due_date") or "").strip()
                if not quarter_label or not due_date:
                    continue
                try:
                    await post_json_with_retry(
                        CALENDAR_SERVICE_URL,
                        json_body={
                            "user_id": user_id,
                            "event_title": f"MTD ITSA quarterly update due ({quarter_label})",
                            "event_date": due_date,
                            "notes": (
                                f"Prepare and submit {quarter_label} quarterly update. "
                                f"Policy: {mtd_obligation.get('policy_code')}"
                            ),
                        },
                        expect_json=False,
                    )
                except httpx.HTTPError:
                    print(f"Warning: Could not create MTD calendar event for {quarter_label}.")


    TAX_SUBMISSIONS_TOTAL.labels(result="success").inc()
    return {
        "submission_id": submission_data.get("submission_id"),
        "message": "Tax return submission has been successfully initiated via integrations service.",
        "submission_mode": submission_mode,
        "mtd_obligation": calculation_result.mtd_obligation,
    }


from .calculators import (
    PAYETaxResult, calculate_paye,
    RentalTaxResult, calculate_rental_tax,
    CISTaxResult, calculate_cis,
    DividendTaxResult, calculate_dividend_tax,
    CryptoTaxResult, calculate_crypto_tax,
)

@app.post("/calculators/paye", response_model=PAYETaxResult)
async def paye_calculator(gross_salary: float, tax_code: str = "1257L"):
    return calculate_paye(gross_salary, tax_code)

@app.post("/calculators/rental", response_model=RentalTaxResult)
async def rental_tax_calculator(
    rental_income: float,
    mortgage_interest: float = 0,
    repairs: float = 0,
    insurance: float = 0,
    letting_agent_fees: float = 0,
    other_expenses: float = 0,
    other_income: float = 0,
):
    return calculate_rental_tax(rental_income, mortgage_interest, repairs, insurance, letting_agent_fees, other_expenses, other_income)

@app.post("/calculators/cis", response_model=CISTaxResult)
async def cis_calculator(gross_payment: float, materials: float = 0, cis_rate: float = 20, other_expenses: float = 0):
    return calculate_cis(gross_payment, materials, cis_rate, other_expenses)

@app.post("/calculators/dividend", response_model=DividendTaxResult)
async def dividend_calculator(dividend_income: float, other_income: float = 0):
    return calculate_dividend_tax(dividend_income, other_income)

@app.post("/calculators/crypto", response_model=CryptoTaxResult)
async def crypto_tax_calculator(total_gains: float, total_losses: float = 0, other_income: float = 0):
    return calculate_crypto_tax(total_gains, total_losses, other_income)


# === Auto-collect and prepare HMRC reports ===


class QuarterDates(BaseModel):
    quarter: str
    tax_year_start: str
    period_start: str
    period_end: str
    due_date: str


class AutoCollectedData(BaseModel):
    period_start: str
    period_end: str
    total_income: float
    income_breakdown: list[dict]
    total_expenses: float
    expense_breakdown: list[dict]
    invoice_income: float
    invoice_count: int
    transaction_count: int
    net_profit: float


class PreparedQuarterlyReport(BaseModel):
    status: str
    quarter: str
    tax_year: str
    collected_data: AutoCollectedData
    hmrc_periodic_update: dict
    estimated_tax: float
    message: str


class PreparedAnnualReport(BaseModel):
    status: str
    tax_year: str
    quarters: list[dict]
    total_income: float
    total_expenses: float
    total_allowances: float
    losses_brought_forward: float
    taxable_income: float
    income_tax: float
    ni_class2: float
    ni_class4: float
    total_tax_due: float
    hmrc_final_declaration: dict
    message: str


def _quarter_dates(tax_year_start_year: int) -> list[QuarterDates]:
    """Generate UK tax year quarter dates."""
    y = tax_year_start_year
    return [
        QuarterDates(quarter="Q1", tax_year_start=f"{y}-04-06", period_start=f"{y}-04-06", period_end=f"{y}-07-05", due_date=f"{y}-08-05"),
        QuarterDates(quarter="Q2", tax_year_start=f"{y}-04-06", period_start=f"{y}-07-06", period_end=f"{y}-10-05", due_date=f"{y}-11-05"),
        QuarterDates(quarter="Q3", tax_year_start=f"{y}-04-06", period_start=f"{y}-10-06", period_end=f"{y+1}-01-05", due_date=f"{y+1}-02-05"),
        QuarterDates(quarter="Q4", tax_year_start=f"{y}-04-06", period_start=f"{y+1}-01-06", period_end=f"{y+1}-04-05", due_date=f"{y+1}-05-05"),
    ]


async def _fetch_transactions(bearer_token: str, from_date: str, to_date: str) -> list[dict]:
    """Fetch user transactions for a date range."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                TRANSACTIONS_SERVICE_URL,
                headers={"Authorization": f"Bearer {bearer_token}"},
                params={"from_date": from_date, "to_date": to_date},
                timeout=15.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


async def _fetch_invoice_income(bearer_token: str, from_date: str, to_date: str) -> dict:
    """Fetch invoice income summary for a date range."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{INVOICE_SERVICE_URL}/reports/summary",
                headers={"Authorization": f"Bearer {bearer_token}"},
                params={"start_date": from_date, "end_date": to_date},
                timeout=15.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"total_billed": 0, "total_collected": 0, "invoice_count": 0}


def _categorize_transactions(transactions: list[dict]) -> AutoCollectedData:
    """Categorize transactions into income and expenses with breakdowns."""
    income_by_category: dict[str, float] = {}
    expense_by_category: dict[str, float] = {}
    total_income = 0.0
    total_expenses = 0.0

    for t in transactions:
        amount = float(t.get("amount", 0))
        category = t.get("category", "uncategorized") or "uncategorized"

        if amount > 0:
            total_income += amount
            income_by_category[category] = income_by_category.get(category, 0) + amount
        elif amount < 0:
            abs_amount = abs(amount)
            total_expenses += abs_amount
            expense_by_category[category] = expense_by_category.get(category, 0) + abs_amount

    income_breakdown = [{"category": k, "amount": round(v, 2)} for k, v in sorted(income_by_category.items(), key=lambda x: -x[1])]
    expense_breakdown = [{"category": k, "amount": round(v, 2)} for k, v in sorted(expense_by_category.items(), key=lambda x: -x[1])]

    return AutoCollectedData(
        period_start="",
        period_end="",
        total_income=round(total_income, 2),
        income_breakdown=income_breakdown,
        total_expenses=round(total_expenses, 2),
        expense_breakdown=expense_breakdown,
        invoice_income=0,
        invoice_count=0,
        transaction_count=len(transactions),
        net_profit=round(total_income - total_expenses, 2),
    )


_HMRC_EXPENSE_MAP = {
    "fuel": "travelCosts",
    "transport": "travelCosts",
    "travel": "travelCosts",
    "rent": "premisesRunningCosts",
    "utilities": "premisesRunningCosts",
    "office_supplies": "adminCosts",
    "home_office": "premisesRunningCosts",
    "advertising": "advertisingCosts",
    "professional_services": "professionalFees",
    "insurance": "other",
    "subscriptions": "adminCosts",
    "food_and_drink": "other",
    "groceries": "other",
    "health": "other",
    "tax": "other",
}


@app.post("/prepare/quarterly", response_model=PreparedQuarterlyReport)
async def prepare_quarterly_report(
    tax_year: int = 2025,
    quarter: str = "Q1",
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    """
    Auto-collect data from transactions + invoices and prepare a quarterly HMRC report.
    Returns ready-to-review report. User must confirm before submission.
    """
    quarters = _quarter_dates(tax_year)
    q = next((q for q in quarters if q.quarter == quarter), None)
    if not q:
        raise HTTPException(status_code=400, detail=f"Invalid quarter: {quarter}. Use Q1, Q2, Q3, or Q4")

    transactions = await _fetch_transactions(bearer_token, q.period_start, q.period_end)
    collected = _categorize_transactions(transactions)
    collected.period_start = q.period_start
    collected.period_end = q.period_end

    invoice_data = await _fetch_invoice_income(bearer_token, q.period_start, q.period_end)
    collected.invoice_income = float(invoice_data.get("total_collected", 0))
    collected.invoice_count = int(invoice_data.get("invoice_count", 0))

    turnover = collected.total_income if collected.total_income > 0 else collected.invoice_income

    hmrc_expenses: dict[str, float] = {
        "costOfGoods": 0, "staffCosts": 0, "travelCosts": 0,
        "premisesRunningCosts": 0, "adminCosts": 0, "advertisingCosts": 0,
        "professionalFees": 0, "other": 0,
    }
    for item in collected.expense_breakdown:
        hmrc_field = _HMRC_EXPENSE_MAP.get(item["category"], "other")
        hmrc_expenses[hmrc_field] += item["amount"]

    hmrc_expenses = {k: round(v, 2) for k, v in hmrc_expenses.items()}

    hmrc_payload = {
        "periodDates": {
            "periodStartDate": q.period_start,
            "periodEndDate": q.period_end,
        },
        "periodIncome": {
            "turnover": round(turnover, 2),
            "other": 0,
        },
        "periodExpenses": hmrc_expenses,
    }

    annual_profit = max((turnover - collected.total_expenses) * 4, 0)
    estimated_tax = 0.0
    taxable = max(annual_profit - 12570, 0)
    estimated_tax += min(taxable, 37700) * 0.20
    if taxable > 37700:
        estimated_tax += min(taxable - 37700, 87440) * 0.40
    estimated_tax = round(estimated_tax / 4, 2)

    return PreparedQuarterlyReport(
        status="ready_for_review",
        quarter=quarter,
        tax_year=f"{tax_year}/{tax_year + 1}",
        collected_data=collected,
        hmrc_periodic_update=hmrc_payload,
        estimated_tax=estimated_tax,
        message=f"Quarterly report for {quarter} ({q.period_start} to {q.period_end}) prepared. "
                f"Income: \u00a3{turnover:.2f}, Expenses: \u00a3{collected.total_expenses:.2f}, "
                f"Estimated quarterly tax: \u00a3{estimated_tax:.2f}. "
                f"Review and confirm to submit to HMRC.",
    )


@app.post("/prepare/annual", response_model=PreparedAnnualReport)
async def prepare_annual_report(
    tax_year: int = 2025,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    """
    Auto-collect full year data and prepare final declaration for HMRC.
    Returns ready-to-review report. User must confirm before submission.
    """
    start = f"{tax_year}-04-06"
    end = f"{tax_year + 1}-04-05"

    transactions = await _fetch_transactions(bearer_token, start, end)
    collected = _categorize_transactions(transactions)

    invoice_data = await _fetch_invoice_income(bearer_token, start, end)
    invoice_income = float(invoice_data.get("total_collected", 0))

    total_income = max(collected.total_income, invoice_income)
    total_expenses = collected.total_expenses

    personal_allowance = 12570.0
    taxable = max(total_income - total_expenses - personal_allowance, 0)

    income_tax = 0.0
    remaining = taxable
    basic = min(remaining, 37700)
    income_tax += basic * 0.20
    remaining -= basic
    higher = min(remaining, 87440) if remaining > 0 else 0
    income_tax += higher * 0.40
    remaining -= higher
    if remaining > 0:
        income_tax += remaining * 0.45

    profit = max(total_income - total_expenses, 0)
    ni4 = 0.0
    if profit > 12570:
        ni4 += min(profit - 12570, 50270 - 12570) * 0.06
        if profit > 50270:
            ni4 += (profit - 50270) * 0.02
    ni2 = 179.40 if profit > 12570 else 0

    total_tax = round(income_tax + ni4 + ni2, 2)

    hmrc_payload = {
        "tax_year_start": start,
        "tax_year_end": end,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_allowances": personal_allowance,
        "loss_brought_forward": 0,
        "declaration": "true_and_complete",
    }

    quarter_summaries = []
    for q in _quarter_dates(tax_year):
        q_transactions = [t for t in transactions if q.period_start <= t.get("date", "") <= q.period_end]
        q_income = sum(float(t.get("amount", 0)) for t in q_transactions if float(t.get("amount", 0)) > 0)
        q_expenses = sum(abs(float(t.get("amount", 0))) for t in q_transactions if float(t.get("amount", 0)) < 0)
        quarter_summaries.append({
            "quarter": q.quarter,
            "period": f"{q.period_start} to {q.period_end}",
            "income": round(q_income, 2),
            "expenses": round(q_expenses, 2),
            "profit": round(q_income - q_expenses, 2),
        })

    return PreparedAnnualReport(
        status="ready_for_review",
        tax_year=f"{tax_year}/{tax_year + 1}",
        quarters=quarter_summaries,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        total_allowances=personal_allowance,
        losses_brought_forward=0,
        taxable_income=round(taxable, 2),
        income_tax=round(income_tax, 2),
        ni_class2=ni2,
        ni_class4=round(ni4, 2),
        total_tax_due=total_tax,
        hmrc_final_declaration=hmrc_payload,
        message=f"Annual report for {tax_year}/{tax_year + 1} prepared. "
                f"Total income: \u00a3{total_income:.2f}, Expenses: \u00a3{total_expenses:.2f}, "
                f"Tax due: \u00a3{total_tax:.2f} (Income Tax: \u00a3{income_tax:.2f} + NI: \u00a3{ni4 + ni2:.2f}). "
                f"Review and confirm to submit to HMRC as Final Declaration.",
    )
