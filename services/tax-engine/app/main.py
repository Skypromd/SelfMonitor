import datetime
import os
import sys
from pathlib import Path
from typing import List, Optional

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
    estimated_tax_due: float
    summary_by_category: List[TaxSummaryItem]

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
    taxable_profit = total_income - total_expenses
    taxable_amount_after_allowance = max(0, taxable_profit - UK_PERSONAL_ALLOWANCE)
    estimated_tax = taxable_amount_after_allowance * UK_BASIC_TAX_RATE

    # 4. Prepare summary
    summary_by_category = [
        TaxSummaryItem(category=cat, total_amount=round(amount, 2), taxable_amount=round(amount, 2)) # Simplified
        for cat, amount in summary_map.items()
    ]

    TAX_CALCULATIONS_TOTAL.labels(result="success").inc()
    return TaxCalculationResult(
        user_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        estimated_tax_due=round(estimated_tax, 2),
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


    TAX_SUBMISSIONS_TOTAL.labels(result="success").inc()
    return {
        "submission_id": submission_data.get("submission_id"),
        "message": "Tax return submission has been successfully initiated via integrations service."
    }
