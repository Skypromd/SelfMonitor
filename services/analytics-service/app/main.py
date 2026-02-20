from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import uuid
import datetime
import os
import httpx
from collections import defaultdict
from fastapi.responses import StreamingResponse
from fpdf import FPDF
import io

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
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

# --- Forecasting Endpoint ---
@app.post("/forecast/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow_forecast(
    request: ForecastRequest,
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL")
    if not TRANSACTIONS_SERVICE_URL:
        raise HTTPException(status_code=500, detail="Transactions service URL not configured")

    # 1. Fetch transactions
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await client.get(TRANSACTIONS_SERVICE_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            transactions = [Transaction(**t) for t in response.json()]
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to transactions-service: {e}")

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
async def get_mortgage_readiness_report(
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL")
    # 1. Fetch transactions (similar to cash flow)
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await client.get(TRANSACTIONS_SERVICE_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            transactions = [Transaction(**t) for t in response.json()]
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to transactions-service: {e}")

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
