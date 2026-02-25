import logging
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
import datetime
import os
import httpx
from .telemetry import setup_telemetry

logger = logging.getLogger(__name__)

# --- Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/transactions/me")
INTEGRATIONS_SERVICE_URL = os.getenv("INTEGRATIONS_SERVICE_URL", "http://localhost:8010/integrations/hmrc/submit-tax-return")
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8015/events")
DEDUCTIBLE_EXPENSE_CATEGORIES = {"transport", "subscriptions", "office_supplies"}
UK_PERSONAL_ALLOWANCE = 12570.0
UK_BASIC_TAX_RATE = 0.20

# --- Security ---
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    return user_id

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
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/calculate", response_model=TaxCalculationResult)
async def calculate_tax(
    request: TaxCalculationRequest, 
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    if request.start_date > request.end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date cannot be before start date.")
    if request.jurisdiction != "UK":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'UK' jurisdiction is supported.")

    # 1. Fetch all transactions for the user from the transactions-service
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await client.get(TRANSACTIONS_SERVICE_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            transactions_data = response.json()
            transactions = [Transaction(**t) for t in transactions_data]
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not connect to transactions-service: {e}")

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
    auth_token: str = Depends(oauth2_scheme),
):
    calculation_result = await calculate_tax(request, user_id, auth_token)

    # 5. Submit the calculated tax to the integrations service
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            submission_payload = {
                "tax_period_start": request.start_date.isoformat(),
                "tax_period_end": request.end_date.isoformat(),
                "tax_due": calculation_result.estimated_tax_due,
            }
            response = await client.post(INTEGRATIONS_SERVICE_URL, headers=headers, json=submission_payload, timeout=15.0)
            response.raise_for_status()
            submission_data = response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not connect to integrations-service: {e}")

    # 6. Create a calendar event for the payment deadline
    try:
        async with httpx.AsyncClient() as client:
            # UK Self Assessment payment deadline is 31st Jan of the next year
            deadline_year = request.end_date.year + 1
            deadline = datetime.date(deadline_year, 1, 31)
            await client.post(
                CALENDAR_SERVICE_URL,
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "user_id": user_id,
                    "event_title": "UK Self Assessment Tax Payment Due",
                    "event_date": deadline.isoformat(),
                    "notes": f"Estimated tax due: £{calculation_result.estimated_tax_due}. Submission ID: {submission_data.get('submission_id')}",
                },
            )
    except httpx.RequestError:
        # This is a non-critical step, so we don't fail the whole request if it fails.
        logger.warning("Could not create calendar event.")


    return {
        "submission_id": submission_data.get("submission_id"),
        "message": "Tax return submission has been successfully initiated via integrations service."
    }
