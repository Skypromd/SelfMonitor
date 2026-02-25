from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import datetime
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from .telemetry import setup_telemetry

# --- Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/transactions/me")
INTEGRATIONS_SERVICE_URL = os.getenv("INTEGRATIONS_SERVICE_URL", "http://localhost:8010/integrations/hmrc/submit-tax-return")
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://localhost:8015/events")
USER_PROFILE_SERVICE_URL = os.getenv("USER_PROFILE_SERVICE_URL", "http://localhost:8001")

# UK tax configuration (defaults are 2024/25 rates; override via env for updates).
UK_PERSONAL_ALLOWANCE = float(os.getenv("UK_PERSONAL_ALLOWANCE", "12570"))
UK_PERSONAL_ALLOWANCE_TAPER_START = float(os.getenv("UK_PERSONAL_ALLOWANCE_TAPER_START", "100000"))
UK_BASIC_RATE_LIMIT = float(os.getenv("UK_BASIC_RATE_LIMIT", "37700"))
UK_HIGHER_RATE_LIMIT = float(os.getenv("UK_HIGHER_RATE_LIMIT", "125140"))
UK_BASIC_TAX_RATE = float(os.getenv("UK_BASIC_TAX_RATE", "0.20"))
UK_HIGHER_TAX_RATE = float(os.getenv("UK_HIGHER_TAX_RATE", "0.40"))
UK_ADDITIONAL_TAX_RATE = float(os.getenv("UK_ADDITIONAL_TAX_RATE", "0.45"))

UK_CLASS2_WEEKLY = float(os.getenv("UK_CLASS2_WEEKLY", "3.45"))
UK_CLASS2_SMALL_PROFITS_THRESHOLD = float(os.getenv("UK_CLASS2_SMALL_PROFITS_THRESHOLD", "6725"))
UK_CLASS4_LOWER_PROFITS_LIMIT = float(os.getenv("UK_CLASS4_LOWER_PROFITS_LIMIT", "12570"))
UK_CLASS4_UPPER_PROFITS_LIMIT = float(os.getenv("UK_CLASS4_UPPER_PROFITS_LIMIT", "50270"))
UK_CLASS4_MAIN_RATE = float(os.getenv("UK_CLASS4_MAIN_RATE", "0.09"))
UK_CLASS4_ADDITIONAL_RATE = float(os.getenv("UK_CLASS4_ADDITIONAL_RATE", "0.02"))
UK_TAX_WEEKS_IN_YEAR = int(os.getenv("UK_TAX_WEEKS_IN_YEAR", "52"))

INCOME_CATEGORIES = {"turnover", "other_business_income"}
DISALLOWABLE_CATEGORIES = {"disallowable", "personal", "private_use", "client_entertainment"}
DEFAULT_EXPENSE_CATEGORY = "other_expenses"
DEFAULT_INCOME_CATEGORY = "turnover"
SA103_CATEGORIES = {
    "turnover",
    "other_business_income",
    "cost_of_goods",
    "premises",
    "repairs",
    "travel",
    "vehicle",
    "wages",
    "subcontractors",
    "legal_professional",
    "advertising",
    "office",
    "bank_charges",
    "other_expenses",
    "capital_allowances",
    "disallowable",
}

CATEGORY_TO_SA103 = {
    "income": "turnover",
    "salary": "turnover",
    "sales": "turnover",
    "bank_interest": "other_business_income",
    "interest": "other_business_income",
    "transport": "travel",
    "travel": "travel",
    "subsistence": "travel",
    "vehicle": "vehicle",
    "fuel": "vehicle",
    "office_supplies": "office",
    "office": "office",
    "subscriptions": "office",
    "software": "office",
    "rent": "premises",
    "utilities": "premises",
    "repairs": "repairs",
    "maintenance": "repairs",
    "advertising": "advertising",
    "marketing": "advertising",
    "legal": "legal_professional",
    "accounting": "legal_professional",
    "bank_fees": "bank_charges",
    "charges": "bank_charges",
    "wages": "wages",
    "payroll": "wages",
    "subcontractors": "subcontractors",
    "capital": "capital_allowances",
    "other": "other_expenses",
    "groceries": "disallowable",
    "food_and_drink": "disallowable",
    "entertainment": "disallowable",
    "personal": "disallowable",
}

# Security
import httpx
from fastapi.security import OAuth2PasswordBearer

security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_subscription_plan(user_id: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{USER_PROFILE_SERVICE_URL}/subscriptions/me",
                headers={"Authorization": "Bearer fake-token"},
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("subscription_plan", "free")
    except httpx.RequestError:
        return "free"
    return "free"

async def require_pro(user_id: str):
    plan = await get_subscription_plan(user_id)
    if plan != "pro":
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Pro subscription required.")

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
    description: Optional[str] = None
    category: Optional[str] = None
    tax_category: Optional[str] = None
    business_use_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Business-use percentage (0-100).",
    )


class ManualAdjustment(BaseModel):
    date: Optional[datetime.date] = None
    description: Optional[str] = None
    amount: float
    tax_category: Optional[str] = None
    business_use_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Business-use percentage (0-100).",
    )

class TaxCalculationRequest(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    jurisdiction: str
    manual_adjustments: Optional[List[ManualAdjustment]] = None

class TaxSummaryItem(BaseModel):
    category: str
    total_amount: float
    allowable_amount: float
    disallowable_amount: float

class TaxCalculationResult(BaseModel):
    user_id: str
    start_date: datetime.date
    end_date: datetime.date
    total_income: float
    total_expenses: float
    total_allowable_expenses: float
    total_disallowable_expenses: float
    taxable_profit: float
    income_tax_due: float
    class2_nic: float
    class4_nic: float
    estimated_tax_due: float
    summary_by_category: List[TaxSummaryItem]


def normalize_category(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def resolve_tax_category(record: Transaction) -> str:
    explicit_category = normalize_category(record.tax_category)
    if explicit_category:
        return explicit_category

    category = normalize_category(record.category)
    if category:
        mapped = CATEGORY_TO_SA103.get(category)
        if mapped:
            return mapped
        return category

    if record.amount >= 0:
        return DEFAULT_INCOME_CATEGORY
    return DEFAULT_EXPENSE_CATEGORY


def normalize_business_use_percent(value: Optional[float]) -> float:
    if value is None:
        return 1.0
    return max(0.0, min(100.0, value)) / 100.0


def calculate_personal_allowance(profit: float) -> float:
    if profit <= UK_PERSONAL_ALLOWANCE_TAPER_START:
        return UK_PERSONAL_ALLOWANCE
    reduction = (profit - UK_PERSONAL_ALLOWANCE_TAPER_START) / 2.0
    return max(0.0, UK_PERSONAL_ALLOWANCE - reduction)


def calculate_income_tax(taxable_profit: float) -> float:
    allowance = calculate_personal_allowance(taxable_profit)
    taxable_after_allowance = max(0.0, taxable_profit - allowance)

    basic_band = min(taxable_after_allowance, UK_BASIC_RATE_LIMIT)
    higher_band = min(
        max(taxable_after_allowance - UK_BASIC_RATE_LIMIT, 0.0),
        max(UK_HIGHER_RATE_LIMIT - UK_BASIC_RATE_LIMIT, 0.0),
    )
    additional_band = max(taxable_after_allowance - UK_HIGHER_RATE_LIMIT, 0.0)

    return (
        basic_band * UK_BASIC_TAX_RATE
        + higher_band * UK_HIGHER_TAX_RATE
        + additional_band * UK_ADDITIONAL_TAX_RATE
    )


def calculate_class2_nic(taxable_profit: float) -> float:
    if taxable_profit < UK_CLASS2_SMALL_PROFITS_THRESHOLD:
        return 0.0
    return UK_CLASS2_WEEKLY * UK_TAX_WEEKS_IN_YEAR


def calculate_class4_nic(taxable_profit: float) -> float:
    if taxable_profit <= UK_CLASS4_LOWER_PROFITS_LIMIT:
        return 0.0
    main_band = min(taxable_profit, UK_CLASS4_UPPER_PROFITS_LIMIT) - UK_CLASS4_LOWER_PROFITS_LIMIT
    additional_band = max(taxable_profit - UK_CLASS4_UPPER_PROFITS_LIMIT, 0.0)
    return (main_band * UK_CLASS4_MAIN_RATE) + (additional_band * UK_CLASS4_ADDITIONAL_RATE)

# --- Endpoints ---
@app.post("/calculate", response_model=TaxCalculationResult)
async def calculate_tax(
    request: TaxCalculationRequest, 
    user_id: str = Depends(get_current_user_id)
):
    if request.start_date > request.end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date cannot be before start date.")
    if request.jurisdiction != "UK":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'UK' jurisdiction is supported.")

    # 1. Fetch all transactions for the user from the transactions-service
    try:
        async with httpx.AsyncClient() as client:
            # In a real app, we'd pass the user's auth token here
            headers = {"Authorization": "Bearer fake-token"}
            response = await client.get(TRANSACTIONS_SERVICE_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            transactions_data = response.json()
            transactions = [Transaction(**t) for t in transactions_data]
    except httpx.RequestError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not connect to transactions-service: {e}")

    # 2. Filter transactions by date and calculate totals
    records: List[Transaction] = [
        t for t in transactions if request.start_date <= t.date <= request.end_date
    ]

    if request.manual_adjustments:
        for adjustment in request.manual_adjustments:
            if adjustment.date and not (request.start_date <= adjustment.date <= request.end_date):
                continue
            records.append(
                Transaction(
                    date=adjustment.date or request.start_date,
                    amount=adjustment.amount,
                    description=adjustment.description,
                    tax_category=adjustment.tax_category,
                    business_use_percent=adjustment.business_use_percent,
                )
            )

    total_income = 0.0
    total_allowable_expenses = 0.0
    total_disallowable_expenses = 0.0
    summary_map: Dict[str, Dict[str, float]] = {}

    def ensure_summary(category: str) -> Dict[str, float]:
        summary_map.setdefault(category, {"total": 0.0, "allowable": 0.0, "disallowable": 0.0})
        return summary_map[category]

    for record in records:
        tax_category = resolve_tax_category(record)
        business_ratio = normalize_business_use_percent(record.business_use_percent)
        effective_amount = record.amount * business_ratio

        if tax_category not in SA103_CATEGORIES:
            tax_category = DEFAULT_INCOME_CATEGORY if effective_amount >= 0 else DEFAULT_EXPENSE_CATEGORY

        if effective_amount >= 0:
            income_category = tax_category if tax_category in INCOME_CATEGORIES else DEFAULT_INCOME_CATEGORY
            total_income += effective_amount
            summary = ensure_summary(income_category)
            summary["total"] += effective_amount
        else:
            expense_amount = abs(effective_amount)
            summary = ensure_summary(tax_category)
            summary["total"] += expense_amount
            if tax_category in DISALLOWABLE_CATEGORIES:
                total_disallowable_expenses += expense_amount
                summary["disallowable"] += expense_amount
            else:
                total_allowable_expenses += expense_amount
                summary["allowable"] += expense_amount

    # 3. Apply UK tax rules
    taxable_profit = total_income - total_allowable_expenses
    income_tax_due = calculate_income_tax(taxable_profit)
    class2_nic = calculate_class2_nic(taxable_profit)
    class4_nic = calculate_class4_nic(taxable_profit)
    estimated_tax = income_tax_due + class2_nic + class4_nic

    # 4. Prepare summary
    summary_by_category = [
        TaxSummaryItem(
            category=cat,
            total_amount=round(values["total"], 2),
            allowable_amount=round(values["allowable"], 2),
            disallowable_amount=round(values["disallowable"], 2),
        )
        for cat, values in sorted(summary_map.items())
    ]

    return TaxCalculationResult(
        user_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        total_income=round(total_income, 2),
        total_expenses=round(total_allowable_expenses, 2),
        total_allowable_expenses=round(total_allowable_expenses, 2),
        total_disallowable_expenses=round(total_disallowable_expenses, 2),
        taxable_profit=round(taxable_profit, 2),
        income_tax_due=round(income_tax_due, 2),
        class2_nic=round(class2_nic, 2),
        class4_nic=round(class4_nic, 2),
        estimated_tax_due=round(estimated_tax, 2),
        summary_by_category=summary_by_category,
    )

@app.post("/calculate-and-submit", status_code=status.HTTP_202_ACCEPTED)
async def calculate_and_submit_tax(
    request: TaxCalculationRequest,
    user_id: str = Depends(get_current_user_id)
):
    await require_pro(user_id)
    # This re-uses the logic from the calculate endpoint.
    # In a real app, this logic would be in a shared function.
    calculation_result = await calculate_tax(request, user_id)

    # 5. Submit the calculated tax to the integrations service
    try:
        async with httpx.AsyncClient() as client:
            # Pass user auth token if needed by the integrations service
            headers = {"Authorization": "Bearer fake-token"}
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
            await client.post(CALENDAR_SERVICE_URL, json={
                "user_id": user_id,
                "event_title": "UK Self Assessment Tax Payment Due",
                "event_date": deadline.isoformat(),
                "notes": f"Estimated tax due: £{calculation_result.estimated_tax_due}. Submission ID: {submission_data.get('submission_id')}"
            })
    except httpx.RequestError:
        # This is a non-critical step, so we don't fail the whole request if it fails.
        print("Warning: Could not create calendar event.")


    return {
        "submission_id": submission_data.get("submission_id"),
        "message": "Tax return submission has been successfully initiated via integrations service."
    }
