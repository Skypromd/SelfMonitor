from fastapi import FastAPI, status, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
import uuid
import datetime
import os
import httpx
from collections import defaultdict
from fastapi.responses import StreamingResponse
from fpdf import FPDF
import io
import calendar

# --- Placeholder Security ---
def fake_auth_check() -> str:
    return "fake-user-123"

app = FastAPI(
    title="Analytics Service",
    description="Handles background analytical tasks and data analysis.",
    version="1.0.0"
)

# --- Models ---

class JobRequest(BaseModel):
    job_type: Literal['run_etl_transactions', 'train_categorization_model']
    parameters: Optional[Dict[str, Any]] = None

class JobStatus(BaseModel):
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_type: Literal['run_etl_transactions', 'train_categorization_model']
    status: Literal['pending', 'running', 'completed', 'failed'] = 'pending'
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    finished_at: Optional[datetime.datetime] = None
    result: Optional[Dict[str, Any]] = None

# --- "Database" for jobs ---

fake_jobs_db = {}

def simulate_job_execution(job_id: uuid.UUID):
    """
    Simulates the completion of a background job.
    In a real app, this would be managed by a task queue like Celery.
    """
    job = fake_jobs_db.get(job_id)
    if job and job.status == 'running':
        job.status = 'completed'
        job.finished_at = datetime.datetime.utcnow()
        job.result = {
            "message": f"{job.job_type} finished successfully.",
            "rows_processed": 15000
        }

# --- Endpoints ---

@app.post("/jobs", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def trigger_job(request: JobRequest):
    """
    Accepts a new job request and puts it into a 'pending' state.
    """
    new_job = JobStatus(job_type=request.job_type)
    fake_jobs_db[new_job.job_id] = new_job

    print(f"Job {new_job.job_id} of type '{new_job.job_type}' created.")
    # In a real app, you would now trigger the background task:
    # run_analytics_job.delay(new_job.job_id, request.parameters)

    return new_job

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: uuid.UUID):
    """
    Retrieves the status of a specific job.
    """
    job = fake_jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # To make the demo interactive, simulate the job's progress.
    if job.status == 'pending':
        job.status = 'running'
    elif job.status == 'running':
        # Simulate completion on the next poll
        simulate_job_execution(job.job_id)

    return job

# --- Models for Forecasting ---
class ForecastRequest(BaseModel):
    days_to_forecast: int = 30

class DataPoint(BaseModel):
    date: datetime.date
    balance: float

class CashFlowResponse(BaseModel):
    forecast: List[DataPoint]

class Transaction(BaseModel):
    date: datetime.date
    amount: float
    category: Optional[str] = None
    tax_category: Optional[str] = None
    business_use_percent: Optional[float] = None

class SummaryByCategory(BaseModel):
    category: str
    income_total: float
    expense_total: float
    net_total: float

class PeriodSummary(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    total_income: float
    total_expenses: float
    net_profit: float
    transaction_count: int
    summary_by_category: List[SummaryByCategory]

class ReportingCadenceResponse(BaseModel):
    cadence: Literal["monthly", "quarterly"]
    turnover_last_12_months: float
    threshold: float
    quarterly_required: bool

USER_PROFILE_SERVICE_URL = os.getenv("USER_PROFILE_SERVICE_URL", "http://localhost:8001")
TURNOVER_QUARTERLY_THRESHOLD = float(os.getenv("TURNOVER_QUARTERLY_THRESHOLD", "50000"))

async def fetch_transactions(user_id: str) -> List[Transaction]:
    transactions_service_url = os.getenv("TRANSACTIONS_SERVICE_URL")
    if not transactions_service_url:
        raise HTTPException(status_code=500, detail="Transactions service URL not configured")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": "Bearer fake-token"}
            response = await client.get(transactions_service_url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return [Transaction(**t) for t in response.json()]
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to transactions-service: {e}")

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
        raise HTTPException(status_code=402, detail="Pro subscription required.")

def apply_business_use(amount: float, business_use_percent: Optional[float]) -> float:
    if business_use_percent is None:
        return amount
    return amount * (max(0.0, min(100.0, business_use_percent)) / 100.0)

def summarize_transactions(transactions: List[Transaction], start_date: datetime.date, end_date: datetime.date) -> PeriodSummary:
    total_income = 0.0
    total_expenses = 0.0
    category_map: Dict[str, Dict[str, float]] = {}
    count = 0

    for t in transactions:
        if not (start_date <= t.date <= end_date):
            continue
        count += 1
        amount = apply_business_use(t.amount, t.business_use_percent)
        category = t.tax_category or t.category or ("income" if amount >= 0 else "expense")
        category_map.setdefault(category, {"income": 0.0, "expense": 0.0})
        if amount >= 0:
            total_income += amount
            category_map[category]["income"] += amount
        else:
            total_expenses += abs(amount)
            category_map[category]["expense"] += abs(amount)

    summary_by_category = [
        SummaryByCategory(
            category=cat,
            income_total=round(values["income"], 2),
            expense_total=round(values["expense"], 2),
            net_total=round(values["income"] - values["expense"], 2),
        )
        for cat, values in sorted(category_map.items())
    ]

    net_profit = total_income - total_expenses
    return PeriodSummary(
        start_date=start_date,
        end_date=end_date,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_profit=round(net_profit, 2),
        transaction_count=count,
        summary_by_category=summary_by_category,
    )

# --- Forecasting Endpoint ---
@app.post("/forecast/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow_forecast(
    request: ForecastRequest,
    user_id: str = Depends(fake_auth_check)
):
    transactions = await fetch_transactions(user_id)

    if not transactions:
        return CashFlowResponse(forecast=[])

    # 2. Simple forecasting logic
    transactions.sort(key=lambda t: t.date)
    first_date = transactions[0].date
    last_date = transactions[-1].date

    # Calculate current balance
    current_balance = sum(t.amount for t in transactions)

    # Calculate average daily net change
    if (last_date - first_date).days > 0:
        average_daily_net = current_balance / (last_date - first_date).days
    else:
        average_daily_net = current_balance

    # 3. Generate forecast
    forecast_points = []
    projected_balance = current_balance
    for i in range(request.days_to_forecast):
        future_date = datetime.date.today() + datetime.timedelta(days=i + 1)
        projected_balance += average_daily_net
        forecast_points.append(DataPoint(date=future_date, balance=round(projected_balance, 2)))

    return CashFlowResponse(forecast=forecast_points)

# --- PDF Report Generation ---
@app.get("/reports/mortgage-readiness", response_class=StreamingResponse)
async def get_mortgage_readiness_report(user_id: str = Depends(fake_auth_check)):
    await require_pro(user_id)
    transactions = await fetch_transactions(user_id)

    # 2. Analyze income over the last 12 months
    twelve_months_ago = datetime.date.today() - datetime.timedelta(days=365)
    monthly_income = defaultdict(float)
    for t in transactions:
        if t.date >= twelve_months_ago and t.amount > 0:
            month = t.date.strftime("%Y-%m")
            monthly_income[month] += t.amount

    total_income = sum(monthly_income.values())
    average_monthly_income = total_income / 12 if total_income > 0 else 0

    # 3. Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Mortgage Readiness Report", 0, 1, "C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Generated for user: {user_id}", 0, 1)
    pdf.cell(0, 10, f"Date: {datetime.date.today().isoformat()}", 0, 1)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Income Summary (Last 12 Months)", 0, 1)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Total Gross Income: £{total_income:,.2f}", 0, 1)
    pdf.cell(0, 8, f"Average Monthly Income: £{average_monthly_income:,.2f}", 0, 1)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(40, 10, 'Month', 1)
    pdf.cell(40, 10, 'Income', 1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 12)
    for month, income in sorted(monthly_income.items()):
        pdf.cell(40, 10, month, 1)
        pdf.cell(40, 10, f"£{income:,.2f}", 1)
        pdf.ln()

    # Create a streaming response
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=mortgage_report_{datetime.date.today()}.pdf"
    })


@app.get("/reports/monthly-summary", response_model=PeriodSummary)
async def get_monthly_summary(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user_id: str = Depends(fake_auth_check)
):
    today = datetime.date.today()
    target_year = year or today.year
    target_month = month or today.month
    last_day = calendar.monthrange(target_year, target_month)[1]
    start_date = datetime.date(target_year, target_month, 1)
    end_date = datetime.date(target_year, target_month, last_day)
    transactions = await fetch_transactions(user_id)
    return summarize_transactions(transactions, start_date, end_date)


@app.get("/reports/quarterly-summary", response_model=PeriodSummary)
async def get_quarterly_summary(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    user_id: str = Depends(fake_auth_check)
):
    await require_pro(user_id)
    today = datetime.date.today()
    target_year = year or today.year
    target_quarter = quarter or ((today.month - 1) // 3 + 1)
    if target_quarter not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Quarter must be between 1 and 4.")

    start_month = (target_quarter - 1) * 3 + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(target_year, end_month)[1]
    start_date = datetime.date(target_year, start_month, 1)
    end_date = datetime.date(target_year, end_month, last_day)
    transactions = await fetch_transactions(user_id)
    return summarize_transactions(transactions, start_date, end_date)


@app.get("/reports/profit-loss", response_model=PeriodSummary)
async def get_profit_loss(
    start_date: datetime.date,
    end_date: datetime.date,
    user_id: str = Depends(fake_auth_check)
):
    await require_pro(user_id)
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date.")
    transactions = await fetch_transactions(user_id)
    return summarize_transactions(transactions, start_date, end_date)


@app.get("/reports/tax-year-summary", response_model=PeriodSummary)
async def get_tax_year_summary(
    tax_year: Optional[str] = None,
    user_id: str = Depends(fake_auth_check)
):
    await require_pro(user_id)
    if tax_year:
        try:
            start_str, end_str = tax_year.split("/")
            start_date = datetime.date.fromisoformat(start_str)
            end_date = datetime.date.fromisoformat(end_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="tax_year must be in YYYY-MM-DD/YYYY-MM-DD format.")
    else:
        today = datetime.date.today()
        start_year = today.year if today >= datetime.date(today.year, 4, 6) else today.year - 1
        start_date = datetime.date(start_year, 4, 6)
        end_date = datetime.date(start_year + 1, 4, 5)

    transactions = await fetch_transactions(user_id)
    return summarize_transactions(transactions, start_date, end_date)


@app.get("/reports/reporting-cadence", response_model=ReportingCadenceResponse)
async def get_reporting_cadence(user_id: str = Depends(fake_auth_check)):
    transactions = await fetch_transactions(user_id)
    cutoff = datetime.date.today() - datetime.timedelta(days=365)
    turnover = 0.0
    for t in transactions:
        if t.date < cutoff:
            continue
        if t.amount > 0:
            turnover += t.amount
    quarterly_required = turnover >= TURNOVER_QUARTERLY_THRESHOLD
    cadence = "quarterly" if quarterly_required else "monthly"
    return ReportingCadenceResponse(
        cadence=cadence,
        turnover_last_12_months=round(turnover, 2),
        threshold=TURNOVER_QUARTERLY_THRESHOLD,
        quarterly_required=quarterly_required,
    )
