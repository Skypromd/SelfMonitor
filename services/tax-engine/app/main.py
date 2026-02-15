import datetime
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

# --- Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/transactions/me")
INTEGRATIONS_SERVICE_URL = os.getenv("INTEGRATIONS_SERVICE_URL", "http://localhost:8010/integrations/hmrc/submit-tax-return")
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8015/events")
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

    # 5. Submit the calculated tax to the integrations service
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        submission_payload = {
            "tax_period_start": request.start_date.isoformat(),
            "tax_period_end": request.end_date.isoformat(),
            "tax_due": calculation_result.estimated_tax_due,
        }
        submission_data = await post_json_with_retry(
            INTEGRATIONS_SERVICE_URL,
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
        print("Warning: Could not create calendar event.")

    # 7. Create quarterly MTD reminder events when quarterly updates are required.
    mtd_obligation = (
        calculation_result.mtd_obligation
        if isinstance(calculation_result.mtd_obligation, dict)
        else {}
    )
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
        "mtd_obligation": calculation_result.mtd_obligation,
    }
