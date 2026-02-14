from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
import uuid
import datetime
import os
import sys
from pathlib import Path
import httpx
from collections import defaultdict
from fastapi.responses import StreamingResponse
from fpdf import FPDF
import io

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_http.retry import get_json_with_retry
from .mortgage_requirements import (
    EMPLOYMENT_PROFILE_METADATA,
    LENDER_PROFILE_METADATA,
    MORTGAGE_TYPE_METADATA,
    build_mortgage_document_checklist,
    build_mortgage_pack_index,
    build_mortgage_readiness_assessment,
    build_mortgage_readiness_matrix,
)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Analytics Service",
    description="Handles background analytical tasks and data analysis.",
    version="1.0.0"
)

DOCUMENTS_SERVICE_URL = os.getenv("DOCUMENTS_SERVICE_URL", "http://documents-service/documents")

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
async def trigger_job(request: JobRequest, _user_id: str = Depends(get_current_user_id)):
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
async def get_job_status(job_id: uuid.UUID, _user_id: str = Depends(get_current_user_id)):
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


class MortgageTypeSummary(BaseModel):
    code: str
    label: str
    description: str


class LenderProfileSummary(BaseModel):
    code: str
    label: str
    description: str


class MortgageChecklistRequest(BaseModel):
    mortgage_type: str
    employment_profile: str = "sole_trader"
    include_adverse_credit_pack: bool = False
    lender_profile: str = "high_street_mainstream"


class MortgageDocumentItem(BaseModel):
    code: str
    title: str
    reason: str


class MortgageChecklistResponse(BaseModel):
    jurisdiction: str
    mortgage_type: str
    mortgage_label: str
    mortgage_description: str
    lender_profile: str
    lender_profile_label: str
    employment_profile: str
    required_documents: list[MortgageDocumentItem]
    conditional_documents: list[MortgageDocumentItem]
    lender_notes: list[str]
    next_steps: list[str]


class MortgageReadinessRequest(BaseModel):
    mortgage_type: str
    employment_profile: str = "sole_trader"
    include_adverse_credit_pack: bool = False
    lender_profile: str = "high_street_mainstream"
    max_documents_scan: int = Field(default=300, ge=10, le=2000)


class MortgageReadinessResponse(BaseModel):
    jurisdiction: str
    mortgage_type: str
    mortgage_label: str
    mortgage_description: str
    lender_profile: str
    lender_profile_label: str
    employment_profile: str
    required_documents: list[MortgageDocumentItem]
    conditional_documents: list[MortgageDocumentItem]
    lender_notes: list[str]
    next_steps: list[str]
    next_actions: list[str]
    uploaded_document_count: int
    detected_document_codes: list[str]
    matched_required_documents: list[MortgageDocumentItem]
    missing_required_documents: list[MortgageDocumentItem]
    missing_conditional_documents: list[MortgageDocumentItem]
    required_completion_percent: float
    overall_completion_percent: float
    readiness_status: Literal["not_ready", "almost_ready", "ready_for_broker_review"]
    readiness_summary: str


class MortgageReadinessMatrixRequest(BaseModel):
    employment_profile: str = "sole_trader"
    include_adverse_credit_pack: bool = False
    lender_profile: str = "high_street_mainstream"
    max_documents_scan: int = Field(default=300, ge=10, le=2000)


class MortgageReadinessMatrixItem(BaseModel):
    mortgage_type: str
    mortgage_label: str
    required_completion_percent: float
    overall_completion_percent: float
    readiness_status: Literal["not_ready", "almost_ready", "ready_for_broker_review"]
    missing_required_count: int
    missing_required_documents: list[MortgageDocumentItem]
    next_actions: list[str]


class MortgageReadinessMatrixResponse(BaseModel):
    jurisdiction: str
    employment_profile: str
    lender_profile: str
    lender_profile_label: str
    include_adverse_credit_pack: bool
    uploaded_document_count: int
    total_mortgage_types: int
    ready_for_broker_review_count: int
    almost_ready_count: int
    not_ready_count: int
    average_required_completion_percent: float
    average_overall_completion_percent: float
    overall_status: Literal["not_ready", "almost_ready", "ready_for_broker_review"]
    items: list[MortgageReadinessMatrixItem]


class MortgagePackIndexRequest(BaseModel):
    mortgage_type: str
    employment_profile: str = "sole_trader"
    include_adverse_credit_pack: bool = False
    lender_profile: str = "high_street_mainstream"
    max_documents_scan: int = Field(default=300, ge=10, le=2000)


class MortgageDocumentEvidenceItem(BaseModel):
    code: str
    title: str
    reason: str
    match_status: Literal["matched", "missing"]
    matched_filenames: list[str]


class MortgagePackIndexResponse(BaseModel):
    jurisdiction: str
    mortgage_type: str
    mortgage_label: str
    mortgage_description: str
    lender_profile: str
    lender_profile_label: str
    employment_profile: str
    required_documents: list[MortgageDocumentItem]
    conditional_documents: list[MortgageDocumentItem]
    lender_notes: list[str]
    next_steps: list[str]
    uploaded_document_count: int
    detected_document_codes: list[str]
    readiness_status: Literal["not_ready", "almost_ready", "ready_for_broker_review"]
    required_completion_percent: float
    overall_completion_percent: float
    readiness_summary: str
    next_actions: list[str]
    matched_required_documents: list[MortgageDocumentItem]
    missing_required_documents: list[MortgageDocumentItem]
    missing_conditional_documents: list[MortgageDocumentItem]
    required_document_evidence: list[MortgageDocumentEvidenceItem]
    conditional_document_evidence: list[MortgageDocumentEvidenceItem]
    generated_at: datetime.datetime

# --- Forecasting Endpoint ---
@app.post("/forecast/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow_forecast(
    request: ForecastRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL")
    if not TRANSACTIONS_SERVICE_URL:
        raise HTTPException(status_code=500, detail="Transactions service URL not configured")

    # 1. Fetch transactions
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        transactions_data = await get_json_with_retry(
            TRANSACTIONS_SERVICE_URL,
            headers=headers,
            timeout=10.0,
        )
        transactions = [Transaction(**t) for t in transactions_data]
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not connect to transactions-service: {exc}") from exc

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


@app.get("/mortgage/types", response_model=list[MortgageTypeSummary])
async def list_supported_mortgage_types(_user_id: str = Depends(get_current_user_id)):
    return [
        MortgageTypeSummary(
            code=code,
            label=metadata["label"],
            description=metadata["description"],
        )
        for code, metadata in MORTGAGE_TYPE_METADATA.items()
    ]


@app.get("/mortgage/lender-profiles", response_model=list[LenderProfileSummary])
async def list_supported_lender_profiles(_user_id: str = Depends(get_current_user_id)):
    return [
        LenderProfileSummary(
            code=code,
            label=metadata["label"],
            description=metadata["description"],
        )
        for code, metadata in LENDER_PROFILE_METADATA.items()
    ]


@app.post("/mortgage/checklist", response_model=MortgageChecklistResponse)
async def generate_mortgage_document_checklist(
    request: MortgageChecklistRequest,
    _user_id: str = Depends(get_current_user_id),
):
    _validate_mortgage_selector_inputs(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        lender_profile=request.lender_profile,
    )
    checklist = build_mortgage_document_checklist(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        lender_profile=request.lender_profile,
    )
    return MortgageChecklistResponse(**checklist)


async def _load_user_uploaded_document_filenames(
    *,
    bearer_token: str,
    max_documents_scan: int,
) -> list[str]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        payload = await get_json_with_retry(
            DOCUMENTS_SERVICE_URL,
            headers=headers,
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not connect to documents-service: {exc}",
        ) from exc

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid documents-service response format",
        )
    filenames: list[str] = []
    for item in payload[:max_documents_scan]:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename")
        if isinstance(filename, str) and filename.strip():
            filenames.append(filename.strip())
    return filenames


def _validate_mortgage_selector_inputs(
    *,
    mortgage_type: str | None,
    employment_profile: str,
    lender_profile: str,
) -> None:
    if mortgage_type is not None and mortgage_type not in MORTGAGE_TYPE_METADATA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mortgage_type '{mortgage_type}'",
        )
    if employment_profile not in EMPLOYMENT_PROFILE_METADATA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported employment_profile '{employment_profile}'",
        )
    if lender_profile not in LENDER_PROFILE_METADATA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported lender_profile '{lender_profile}'",
        )


def _build_mortgage_pack_index_pdf_bytes(pack_index: dict[str, object]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Mortgage Pack Index", 0, 1, "C")
    pdf.set_font("Helvetica", "", 11)
    generated_at = str(pack_index.get("generated_at", ""))
    pdf.cell(0, 7, f"Generated at: {generated_at}", 0, 1)
    pdf.cell(0, 7, f"Mortgage type: {pack_index.get('mortgage_label', '')}", 0, 1)
    pdf.cell(0, 7, f"Lender profile: {pack_index.get('lender_profile_label', '')}", 0, 1)
    pdf.cell(0, 7, f"Employment profile: {pack_index.get('employment_profile', '')}", 0, 1)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Readiness summary", 0, 1)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, str(pack_index.get("readiness_summary", "")))
    pdf.cell(0, 7, f"Required completion: {pack_index.get('required_completion_percent', 0)}%", 0, 1)
    pdf.cell(0, 7, f"Overall completion: {pack_index.get('overall_completion_percent', 0)}%", 0, 1)
    pdf.cell(0, 7, f"Status: {pack_index.get('readiness_status', '')}", 0, 1)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Required document evidence", 0, 1)
    pdf.set_font("Helvetica", "", 10)
    required_evidence = pack_index.get("required_document_evidence", [])
    if isinstance(required_evidence, list):
        for item in required_evidence:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", ""))
            title = str(item.get("title", ""))
            status_value = str(item.get("match_status", "missing"))
            matched_files = item.get("matched_filenames", [])
            matched_files_text = ", ".join(str(name) for name in matched_files[:4]) if isinstance(matched_files, list) else ""
            if not matched_files_text:
                matched_files_text = "not detected"
            pdf.multi_cell(0, 6, f"[{status_value}] {title} ({code})")
            pdf.multi_cell(0, 6, f"Evidence: {matched_files_text}")
            pdf.ln(1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Immediate actions", 0, 1)
    pdf.set_font("Helvetica", "", 10)
    next_actions = pack_index.get("next_actions", [])
    if isinstance(next_actions, list) and next_actions:
        for action in next_actions:
            pdf.multi_cell(0, 6, f"- {action}")
    else:
        pdf.multi_cell(0, 6, "- No immediate actions")

    return pdf.output(dest="S").encode("latin1")


@app.post("/mortgage/readiness", response_model=MortgageReadinessResponse)
async def evaluate_mortgage_readiness(
    request: MortgageReadinessRequest,
    _user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    _validate_mortgage_selector_inputs(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        lender_profile=request.lender_profile,
    )
    checklist = build_mortgage_document_checklist(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        lender_profile=request.lender_profile,
    )
    filenames = await _load_user_uploaded_document_filenames(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    readiness = build_mortgage_readiness_assessment(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    return MortgageReadinessResponse(**readiness)


@app.post("/mortgage/readiness-matrix", response_model=MortgageReadinessMatrixResponse)
async def evaluate_mortgage_readiness_matrix(
    request: MortgageReadinessMatrixRequest,
    _user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    _validate_mortgage_selector_inputs(
        mortgage_type=None,
        employment_profile=request.employment_profile,
        lender_profile=request.lender_profile,
    )
    filenames = await _load_user_uploaded_document_filenames(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    matrix = build_mortgage_readiness_matrix(
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        lender_profile=request.lender_profile,
        uploaded_filenames=filenames,
    )
    return MortgageReadinessMatrixResponse(**matrix)


@app.post("/mortgage/pack-index", response_model=MortgagePackIndexResponse)
async def generate_mortgage_pack_index(
    request: MortgagePackIndexRequest,
    _user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    _validate_mortgage_selector_inputs(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        lender_profile=request.lender_profile,
    )
    checklist = build_mortgage_document_checklist(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        lender_profile=request.lender_profile,
    )
    filenames = await _load_user_uploaded_document_filenames(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    pack_index = build_mortgage_pack_index(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    pack_index["generated_at"] = datetime.datetime.now(datetime.UTC)
    return MortgagePackIndexResponse(**pack_index)


@app.post("/mortgage/pack-index.pdf")
async def generate_mortgage_pack_index_pdf(
    request: MortgagePackIndexRequest,
    _user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    _validate_mortgage_selector_inputs(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        lender_profile=request.lender_profile,
    )
    checklist = build_mortgage_document_checklist(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        lender_profile=request.lender_profile,
    )
    filenames = await _load_user_uploaded_document_filenames(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    pack_index = build_mortgage_pack_index(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    generated_at = datetime.datetime.now(datetime.UTC)
    pack_index["generated_at"] = generated_at.isoformat()
    pdf_bytes = _build_mortgage_pack_index_pdf_bytes(pack_index)
    filename_safe_type = request.mortgage_type.replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; "
                f"filename=mortgage_pack_index_{filename_safe_type}_{generated_at.date().isoformat()}.pdf"
            )
        },
    )

# --- PDF Report Generation ---
@app.get("/reports/mortgage-readiness", response_class=StreamingResponse)
async def get_mortgage_readiness_report(
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL")
    # 1. Fetch transactions (similar to cash flow)
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        transactions_data = await get_json_with_retry(
            TRANSACTIONS_SERVICE_URL,
            headers=headers,
            timeout=10.0,
        )
        transactions = [Transaction(**t) for t in transactions_data]
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not connect to transactions-service: {exc}") from exc

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
