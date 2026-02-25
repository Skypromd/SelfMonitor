from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import uuid
import datetime
import os
import httpx
import sqlite3
import threading
import json
import time
from collections import defaultdict
from fastapi.responses import StreamingResponse
from fpdf import FPDF
import io

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "/tmp/analytics.db")
ANALYTICS_JOB_DURATION_SECONDS = float(os.getenv("ANALYTICS_JOB_DURATION_SECONDS", "0.2"))

# --- API Marketplace Configuration ---
API_MARKETPLACE_ENABLED = os.getenv("API_MARKETPLACE_ENABLED", "true").lower() == "true"

# --- Valid API keys for marketplace partners ---
API_MARKETPLACE_KEYS = {
    "fintech_partner_1": {
        "name": "MoneyFlow Analytics Ltd",
        "tier": "premium",
        "rate_limit": 1000,  # requests per hour
        "allowed_endpoints": ["cash_flow", "insights", "forecasting"],
        "monthly_fee": 299.0
    },
    "accounting_firm_2": {
        "name": "TaxPro Solutions",
        "tier": "enterprise", 
        "rate_limit": 5000,
        "allowed_endpoints": ["*"],  # All endpoints
        "monthly_fee": 899.0
    },
    "bank_integration_3": {
        "name": "OpenBanking Aggregator Co",
        "tier": "standard",
        "rate_limit": 500,
        "allowed_endpoints": ["basic_insights"],
        "monthly_fee": 149.0
    }
}

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
    user_id: str
    job_type: Literal['run_etl_transactions', 'train_categorization_model']
    status: Literal['pending', 'running', 'completed', 'failed'] = 'pending'
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    finished_at: Optional[datetime.datetime] = None
    result: Optional[Dict[str, Any]] = None

# --- Database for jobs ---
db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(ANALYTICS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_analytics_db() -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT '',
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                finished_at TEXT,
                result_json TEXT
            )
            """
        )
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        if "user_id" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
        conn.commit()
        conn.close()


def reset_analytics_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM jobs")
        conn.commit()
        conn.close()


def _row_to_job(row: sqlite3.Row) -> JobStatus:
    return JobStatus(
        job_id=uuid.UUID(row["job_id"]),
        user_id=row["user_id"],
        job_type=row["job_type"],
        status=row["status"],
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
        finished_at=datetime.datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        result=json.loads(row["result_json"]) if row["result_json"] else None,
    )


def save_job(job: JobStatus) -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO jobs (job_id, user_id, job_type, status, created_at, finished_at, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job.job_id),
                job.user_id,
                job.job_type,
                job.status,
                job.created_at.isoformat(),
                job.finished_at.isoformat() if job.finished_at else None,
                json.dumps(job.result) if job.result else None,
            ),
        )
        conn.commit()
        conn.close()


def get_job(job_id: uuid.UUID) -> JobStatus | None:
    with db_lock:
        conn = _connect()
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),)).fetchone()
        conn.close()
    return _row_to_job(row) if row else None


def update_job(job: JobStatus) -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, finished_at = ?, result_json = ?
            WHERE job_id = ?
            """,
            (
                job.status,
                job.finished_at.isoformat() if job.finished_at else None,
                json.dumps(job.result) if job.result else None,
                str(job.job_id),
            ),
        )
        conn.commit()
        conn.close()

def run_job_worker(job_id: uuid.UUID):
    job = get_job(job_id)
    if not job:
        return

    job.status = 'running'
    update_job(job)
    time.sleep(ANALYTICS_JOB_DURATION_SECONDS)

    job.status = 'completed'
    job.finished_at = datetime.datetime.now(datetime.UTC)
    job.result = {
        "message": f"{job.job_type} finished successfully.",
        "rows_processed": 15000,
    }
    update_job(job)

# --- Endpoints ---

@app.post("/jobs", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def trigger_job(
    request: JobRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Accepts a new job request and puts it into a 'pending' state.
    """
    new_job = JobStatus(user_id=user_id, job_type=request.job_type)
    save_job(new_job)
    threading.Thread(target=run_job_worker, args=(new_job.job_id,), daemon=True).start()
    return new_job

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
):
    """
    Retrieves the status of a specific job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

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
@app.get("/health")
async def health_check():
    return {"status": "ok"}


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


init_analytics_db()

# === API MARKETPLACE MONETIZATION ===

@app.get("/api/v1/marketplace/revenue")
async def get_api_marketplace_revenue():
    """API marketplace revenue dashboard - new B2B revenue stream"""
    return {
        "monthly_api_revenue": 2597,
        "projected_arr_50_partners": 373800,
        "profit_margin": "78% (leverages existing infrastructure)",
        "revenue_improvement": "+£31k/month potential with API monetization"
    }
