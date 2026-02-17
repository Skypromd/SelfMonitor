from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
import uuid
import datetime
import os
import sys
from pathlib import Path
import httpx
from collections import defaultdict, deque
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
    build_mortgage_evidence_quality_checks,
    build_mortgage_document_checklist,
    build_mortgage_lender_fit_snapshot,
    build_mortgage_pack_index,
    build_mortgage_refresh_reminders,
    build_mortgage_readiness_assessment,
    build_mortgage_readiness_matrix,
    build_mortgage_submission_gate,
)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Analytics Service",
    description="Handles background analytical tasks and data analysis.",
    version="1.0.0"
)


def _parse_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return default
    return parsed_value if parsed_value > 0 else default


DOCUMENTS_SERVICE_URL = os.getenv("DOCUMENTS_SERVICE_URL", "http://documents-service/documents")
USER_PROFILE_SERVICE_URL = os.getenv("USER_PROFILE_SERVICE_URL", "http://user-profile-service/profiles/me")
MOBILE_ANALYTICS_INGEST_API_KEY = os.getenv("MOBILE_ANALYTICS_INGEST_API_KEY", "").strip()
MOBILE_ANALYTICS_MAX_EVENTS = max(100, _parse_positive_int_env("MOBILE_ANALYTICS_MAX_EVENTS", 5000))
MOBILE_ONBOARDING_EXPERIMENT_ID = os.getenv("MOBILE_ONBOARDING_EXPERIMENT_ID", "mobile-onboarding-v1")
MOBILE_ONBOARDING_FORCE_VARIANT_ID = os.getenv("MOBILE_ONBOARDING_FORCE_VARIANT_ID", "").strip() or None
MOBILE_SPLASH_TITLE = os.getenv("MOBILE_SPLASH_TITLE", "SelfMonitor")
MOBILE_SPLASH_SUBTITLE = os.getenv(
    "MOBILE_SPLASH_SUBTITLE",
    "World-class finance copilot for UK self-employed.",
)
MOBILE_SPLASH_GRADIENT = os.getenv(
    "MOBILE_SPLASH_GRADIENT",
    "#0b1120,#1e3a8a,#3b82f6",
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


DEFAULT_MOBILE_ONBOARDING_VARIANTS: list[dict[str, Any]] = [
    {
        "id": "velocity",
        "title": "Start in minutes",
        "subtitle": "Connect finances, scan receipts, and stay ahead of tax/reporting deadlines.",
        "ctaLabel": "Start now",
        "features": [
            "Fast receipt scan and smart categorisation",
            "HMRC and invoice reminder push alerts",
            "Mobile-first control center for your business",
        ],
        "gradient": ["#1d4ed8", "#312e81", "#020617"],
        "weight": 1,
    },
    {
        "id": "security",
        "title": "Fintech-grade security",
        "subtitle": "Secure sessions and biometric unlock by default for account protection.",
        "ctaLabel": "Enable protection",
        "features": [
            "Face/Touch/Fingerprint unlock support",
            "Secure session storage on device",
            "Controlled push deep-link routing",
        ],
        "gradient": ["#0f172a", "#1e3a8a", "#1d4ed8"],
        "weight": 1,
    },
    {
        "id": "investor",
        "title": "Clarity for growth",
        "subtitle": "Track billing, costs, and readiness metrics in one premium mobile experience.",
        "ctaLabel": "Open dashboard",
        "features": [
            "Recurring invoices and reminder operations",
            "Mortgage/readiness document workflows",
            "KPI-focused operating cadence",
        ],
        "gradient": ["#1e3a8a", "#1d4ed8", "#0f172a"],
        "weight": 1,
    },
]


class MobileAnalyticsEventIngestRequest(BaseModel):
    event: str = Field(min_length=1, max_length=120)
    source: str = Field(default="mobile-app", min_length=1, max_length=40)
    platform: str = Field(default="unknown", min_length=2, max_length=32)
    occurred_at: Optional[datetime.datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MobileAnalyticsEventRecord(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event: str
    source: str
    platform: str
    occurred_at: datetime.datetime
    received_at: datetime.datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MobileAnalyticsIngestResponse(BaseModel):
    accepted: bool
    stored_events: int


class MobileOnboardingVariantConfig(BaseModel):
    id: str
    title: str
    subtitle: str
    ctaLabel: str
    features: list[str]
    gradient: list[str]
    weight: int = 1


class MobileOnboardingExperimentConfig(BaseModel):
    experimentId: str
    forceVariantId: Optional[str] = None
    variants: list[MobileOnboardingVariantConfig]


class MobileSplashConfig(BaseModel):
    title: str
    subtitle: str
    gradient: list[str]


class MobileRemoteConfigResponse(BaseModel):
    generated_at: datetime.datetime
    splash: MobileSplashConfig
    onboardingExperiment: MobileOnboardingExperimentConfig


class MobileVariantFunnelPoint(BaseModel):
    variant_id: str
    impressions: int
    cta_taps: int
    completions: int
    completion_rate_percent: Optional[float] = None


class MobileAnalyticsFunnelResponse(BaseModel):
    window_days: int
    generated_at: datetime.datetime
    total_events: int
    splash_impressions: int
    splash_dismissed: int
    onboarding_impressions: int
    onboarding_cta_taps: int
    onboarding_completions: int
    biometric_gate_shown: int
    biometric_successes: int
    push_permission_prompted: int
    push_permission_granted: int
    push_deep_link_opened: int
    splash_to_onboarding_rate_percent: Optional[float] = None
    onboarding_completion_rate_percent: Optional[float] = None
    cta_to_completion_rate_percent: Optional[float] = None
    biometric_success_rate_percent: Optional[float] = None
    push_opt_in_rate_percent: Optional[float] = None
    variants: list[MobileVariantFunnelPoint] = Field(default_factory=list)


def _normalize_gradient_triplet(raw_gradient: str) -> list[str]:
    colors = [item.strip() for item in raw_gradient.split(",") if item.strip()]
    if len(colors) < 3:
        return ["#0b1120", "#1e3a8a", "#3b82f6"]
    return colors[:3]


def _build_mobile_remote_config_payload() -> MobileRemoteConfigResponse:
    variants = [
        MobileOnboardingVariantConfig(
            id=str(item["id"]),
            title=str(item["title"]),
            subtitle=str(item["subtitle"]),
            ctaLabel=str(item["ctaLabel"]),
            features=[str(feature) for feature in item.get("features", [])],
            gradient=[str(color) for color in item.get("gradient", [])][:3],
            weight=int(item.get("weight", 1)),
        )
        for item in DEFAULT_MOBILE_ONBOARDING_VARIANTS
    ]
    return MobileRemoteConfigResponse(
        generated_at=datetime.datetime.now(datetime.UTC),
        splash=MobileSplashConfig(
            title=MOBILE_SPLASH_TITLE,
            subtitle=MOBILE_SPLASH_SUBTITLE,
            gradient=_normalize_gradient_triplet(MOBILE_SPLASH_GRADIENT),
        ),
        onboardingExperiment=MobileOnboardingExperimentConfig(
            experimentId=MOBILE_ONBOARDING_EXPERIMENT_ID,
            forceVariantId=MOBILE_ONBOARDING_FORCE_VARIANT_ID,
            variants=variants,
        ),
    )


def _require_mobile_analytics_api_key(x_api_key: str | None = Header(default=None, alias="X-Api-Key")) -> None:
    if MOBILE_ANALYTICS_INGEST_API_KEY and x_api_key != MOBILE_ANALYTICS_INGEST_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid analytics API key",
        )


def _safe_percent(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _extract_variant_id(metadata: Dict[str, Any]) -> Optional[str]:
    candidate = metadata.get("onboarding_variant")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None

# --- "Database" for jobs ---

fake_jobs_db = {}
mobile_analytics_events: deque[MobileAnalyticsEventRecord] = deque(maxlen=MOBILE_ANALYTICS_MAX_EVENTS)

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


@app.get("/mobile/config", response_model=MobileRemoteConfigResponse)
async def get_mobile_remote_config():
    """
    Returns remote configuration payload for branded splash and onboarding experiments.
    """
    return _build_mobile_remote_config_payload()


@app.post("/mobile/analytics/events", response_model=MobileAnalyticsIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_mobile_analytics_event(
    request: MobileAnalyticsEventIngestRequest,
    _api_guard: None = Depends(_require_mobile_analytics_api_key),
):
    """
    Accepts a mobile analytics event for funnel analysis.
    """
    occurred_at = request.occurred_at or datetime.datetime.now(datetime.UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=datetime.UTC)
    else:
        occurred_at = occurred_at.astimezone(datetime.UTC)

    mobile_analytics_events.append(
        MobileAnalyticsEventRecord(
            event=request.event.strip(),
            source=request.source.strip(),
            platform=request.platform.strip().lower(),
            occurred_at=occurred_at,
            received_at=datetime.datetime.now(datetime.UTC),
            metadata=request.metadata,
        )
    )
    return MobileAnalyticsIngestResponse(accepted=True, stored_events=len(mobile_analytics_events))


@app.get("/mobile/analytics/funnel", response_model=MobileAnalyticsFunnelResponse)
async def get_mobile_analytics_funnel(
    days: int = Query(default=14, ge=1, le=90),
    _api_guard: None = Depends(_require_mobile_analytics_api_key),
):
    """
    Returns aggregate onboarding/security funnel metrics for the selected lookback window.
    """
    now_utc = datetime.datetime.now(datetime.UTC)
    cutoff = now_utc - datetime.timedelta(days=days)
    window_events = [event for event in mobile_analytics_events if event.occurred_at >= cutoff]

    def count(event_name: str) -> int:
        return sum(1 for item in window_events if item.event == event_name)

    splash_impressions = count("mobile.splash.impression")
    splash_dismissed = count("mobile.splash.dismissed")
    onboarding_impressions = count("mobile.onboarding.impression")
    onboarding_cta_taps = count("mobile.onboarding.cta_tapped")
    onboarding_completions = count("mobile.onboarding.completed")
    biometric_gate_shown = count("mobile.biometric.gate_shown")
    biometric_successes = count("mobile.biometric.challenge_succeeded")
    push_permission_prompted = count("mobile.push.permission_prompted")
    push_permission_granted = count("mobile.push.permission_granted")
    push_deep_link_opened = count("mobile.push.deep_link_opened") + count("mobile.push.deep_link_cold_start")

    variant_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"impressions": 0, "cta_taps": 0, "completions": 0}
    )
    for item in window_events:
        variant_id = _extract_variant_id(item.metadata)
        if not variant_id:
            continue
        if item.event == "mobile.onboarding.impression":
            variant_buckets[variant_id]["impressions"] += 1
        elif item.event == "mobile.onboarding.cta_tapped":
            variant_buckets[variant_id]["cta_taps"] += 1
        elif item.event == "mobile.onboarding.completed":
            variant_buckets[variant_id]["completions"] += 1

    variant_points = [
        MobileVariantFunnelPoint(
            variant_id=variant_id,
            impressions=bucket["impressions"],
            cta_taps=bucket["cta_taps"],
            completions=bucket["completions"],
            completion_rate_percent=_safe_percent(bucket["completions"], bucket["impressions"]),
        )
        for variant_id, bucket in sorted(
            variant_buckets.items(),
            key=lambda item: item[1]["impressions"],
            reverse=True,
        )
    ]

    return MobileAnalyticsFunnelResponse(
        window_days=days,
        generated_at=now_utc,
        total_events=len(window_events),
        splash_impressions=splash_impressions,
        splash_dismissed=splash_dismissed,
        onboarding_impressions=onboarding_impressions,
        onboarding_cta_taps=onboarding_cta_taps,
        onboarding_completions=onboarding_completions,
        biometric_gate_shown=biometric_gate_shown,
        biometric_successes=biometric_successes,
        push_permission_prompted=push_permission_prompted,
        push_permission_granted=push_permission_granted,
        push_deep_link_opened=push_deep_link_opened,
        splash_to_onboarding_rate_percent=_safe_percent(onboarding_impressions, splash_impressions),
        onboarding_completion_rate_percent=_safe_percent(onboarding_completions, onboarding_impressions),
        cta_to_completion_rate_percent=_safe_percent(onboarding_completions, onboarding_cta_taps),
        biometric_success_rate_percent=_safe_percent(biometric_successes, biometric_gate_shown),
        push_opt_in_rate_percent=_safe_percent(push_permission_granted, push_permission_prompted),
        variants=variant_points,
    )

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


class MortgageEvidenceQualityIssue(BaseModel):
    check_type: Literal["staleness", "name_mismatch", "period_mismatch", "unreadable_ocr"]
    severity: Literal["critical", "warning", "info"]
    document_filename: str
    document_code: Optional[str] = None
    message: str
    suggested_action: str


class MortgageEvidenceQualitySummary(BaseModel):
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    has_blockers: bool


class MortgageSubmissionGate(BaseModel):
    compliance_disclaimer: str
    advisor_review_required: bool
    advisor_review_confirmed: bool
    broker_submission_allowed: bool
    broker_submission_blockers: list[str]


class MortgageRefreshReminderSummary(BaseModel):
    total_reminders: int
    due_now_count: int
    upcoming_count: int
    has_due_now: bool
    next_due_date: Optional[datetime.date] = None


class MortgageRefreshReminder(BaseModel):
    reminder_type: Literal["statement_refresh", "id_validity_check"]
    document_code: str
    title: str
    cadence_days: int
    due_date: datetime.date
    status: Literal["due_now", "upcoming"]
    document_filename: str
    message: str
    suggested_action: str


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
    advisor_review_confirmed: bool = False


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
    evidence_quality_summary: MortgageEvidenceQualitySummary
    evidence_quality_issues: list[MortgageEvidenceQualityIssue]
    refresh_reminder_summary: MortgageRefreshReminderSummary
    refresh_reminders: list[MortgageRefreshReminder]
    submission_gate: MortgageSubmissionGate


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


class MortgageLenderFitRequest(BaseModel):
    mortgage_type: str
    employment_profile: str = "sole_trader"
    include_adverse_credit_pack: bool = False
    max_documents_scan: int = Field(default=300, ge=10, le=2000)


class MortgageLenderFitItem(BaseModel):
    lender_profile: str
    lender_profile_label: str
    required_completion_percent: float
    overall_completion_percent: float
    readiness_status: Literal["not_ready", "almost_ready", "ready_for_broker_review"]
    missing_required_count: int
    top_missing_required_titles: list[str]
    lender_notes: list[str]
    next_actions: list[str]


class MortgageLenderFitResponse(BaseModel):
    jurisdiction: str
    mortgage_type: str
    mortgage_label: str
    employment_profile: str
    include_adverse_credit_pack: bool
    uploaded_document_count: int
    total_lender_profiles: int
    recommended_lender_profile: str | None = None
    recommended_lender_profile_label: str | None = None
    recommendation_reason: str
    items: list[MortgageLenderFitItem]


class MortgagePackIndexRequest(BaseModel):
    mortgage_type: str
    employment_profile: str = "sole_trader"
    include_adverse_credit_pack: bool = False
    lender_profile: str = "high_street_mainstream"
    max_documents_scan: int = Field(default=300, ge=10, le=2000)
    advisor_review_confirmed: bool = False


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
    evidence_quality_summary: MortgageEvidenceQualitySummary
    evidence_quality_issues: list[MortgageEvidenceQualityIssue]
    refresh_reminder_summary: MortgageRefreshReminderSummary
    refresh_reminders: list[MortgageRefreshReminder]
    submission_gate: MortgageSubmissionGate
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


def _extract_document_filenames(documents: list[dict[str, object]]) -> list[str]:
    filenames: list[str] = []
    for item in documents:
        filename = item.get("filename")
        if isinstance(filename, str) and filename.strip():
            filenames.append(filename.strip())
    return filenames


async def _load_user_uploaded_documents(
    *,
    bearer_token: str,
    max_documents_scan: int,
) -> list[dict[str, object]]:
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
    documents: list[dict[str, object]] = []
    for item in payload[:max_documents_scan]:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename")
        if not isinstance(filename, str) or not filename.strip():
            continue
        documents.append(item)
    return documents


async def _load_user_profile_name(
    *,
    bearer_token: str,
) -> tuple[str | None, str | None]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        payload = await get_json_with_retry(
            USER_PROFILE_SERVICE_URL,
            headers=headers,
            timeout=10.0,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            return None, None
        return None, None
    except httpx.HTTPError:
        return None, None

    if not isinstance(payload, dict):
        return None, None
    first_name = payload.get("first_name")
    last_name = payload.get("last_name")
    return (
        first_name.strip() if isinstance(first_name, str) and first_name.strip() else None,
        last_name.strip() if isinstance(last_name, str) and last_name.strip() else None,
    )


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

    quality_summary = pack_index.get("evidence_quality_summary", {})
    if isinstance(quality_summary, dict):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Evidence quality checks", 0, 1)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Total issues: {quality_summary.get('total_issues', 0)}", 0, 1)
        pdf.cell(
            0,
            7,
            (
                "Critical / Warning / Info: "
                f"{quality_summary.get('critical_count', 0)} / "
                f"{quality_summary.get('warning_count', 0)} / "
                f"{quality_summary.get('info_count', 0)}"
            ),
            0,
            1,
        )
        pdf.ln(2)
        quality_issues = pack_index.get("evidence_quality_issues", [])
        if isinstance(quality_issues, list):
            for issue in quality_issues[:6]:
                if not isinstance(issue, dict):
                    continue
                severity = str(issue.get("severity", "info")).upper()
                filename = str(issue.get("document_filename", ""))
                message = str(issue.get("message", ""))
                pdf.multi_cell(0, 6, f"[{severity}] {filename}: {message}")
            pdf.ln(2)

    submission_gate = pack_index.get("submission_gate", {})
    if isinstance(submission_gate, dict):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Compliance and submission gate", 0, 1)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, str(submission_gate.get("compliance_disclaimer", "")))
        pdf.cell(
            0,
            7,
            f"Advisor review confirmed: {'yes' if submission_gate.get('advisor_review_confirmed') else 'no'}",
            0,
            1,
        )
        pdf.cell(
            0,
            7,
            f"Broker submission allowed: {'yes' if submission_gate.get('broker_submission_allowed') else 'no'}",
            0,
            1,
        )
        blockers = submission_gate.get("broker_submission_blockers", [])
        if isinstance(blockers, list) and blockers:
            pdf.multi_cell(0, 7, "Blockers:")
            for blocker in blockers[:5]:
                pdf.multi_cell(0, 6, f"- {blocker}")
        pdf.ln(2)

    refresh_summary = pack_index.get("refresh_reminder_summary", {})
    if isinstance(refresh_summary, dict):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Monthly refresh reminders", 0, 1)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Total reminders: {refresh_summary.get('total_reminders', 0)}", 0, 1)
        pdf.cell(
            0,
            7,
            (
                "Due now / Upcoming: "
                f"{refresh_summary.get('due_now_count', 0)} / {refresh_summary.get('upcoming_count', 0)}"
            ),
            0,
            1,
        )
        refresh_reminders = pack_index.get("refresh_reminders", [])
        if isinstance(refresh_reminders, list):
            for reminder in refresh_reminders[:6]:
                if not isinstance(reminder, dict):
                    continue
                title = str(reminder.get("title", ""))
                due_date = str(reminder.get("due_date", ""))
                status = str(reminder.get("status", "upcoming"))
                message = str(reminder.get("message", ""))
                pdf.multi_cell(0, 6, f"[{status}] {title} (due: {due_date})")
                pdf.multi_cell(0, 6, message)
        pdf.ln(2)

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
    uploaded_documents = await _load_user_uploaded_documents(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    filenames = _extract_document_filenames(uploaded_documents)
    readiness = build_mortgage_readiness_assessment(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    first_name, last_name = await _load_user_profile_name(bearer_token=bearer_token)
    quality_checks = build_mortgage_evidence_quality_checks(
        uploaded_documents=uploaded_documents,
        applicant_first_name=first_name,
        applicant_last_name=last_name,
    )
    readiness.update(quality_checks)
    refresh_reminders = build_mortgage_refresh_reminders(uploaded_documents=uploaded_documents)
    readiness.update(refresh_reminders)
    submission_gate = build_mortgage_submission_gate(
        readiness_status=str(readiness.get("readiness_status", "")),
        evidence_quality_summary=quality_checks.get("evidence_quality_summary")
        if isinstance(quality_checks.get("evidence_quality_summary"), dict)
        else None,
        advisor_review_confirmed=request.advisor_review_confirmed,
    )
    readiness["submission_gate"] = submission_gate
    quality_summary = quality_checks.get("evidence_quality_summary")
    if isinstance(quality_summary, dict) and bool(quality_summary.get("has_blockers")):
        next_actions = list(readiness.get("next_actions", []))
        blocker_action = "Resolve critical evidence-quality blockers before broker submission."
        if blocker_action not in next_actions:
            readiness["next_actions"] = [blocker_action, *next_actions]
    if not request.advisor_review_confirmed:
        next_actions = list(readiness.get("next_actions", []))
        advisor_action = "Get a qualified mortgage adviser review before broker submission."
        if advisor_action not in next_actions:
            readiness["next_actions"] = [advisor_action, *next_actions]
    refresh_summary = refresh_reminders.get("refresh_reminder_summary")
    if isinstance(refresh_summary, dict) and int(refresh_summary.get("due_now_count", 0)) > 0:
        next_actions = list(readiness.get("next_actions", []))
        due_now_count = int(refresh_summary.get("due_now_count", 0))
        refresh_action = (
            f"Refresh {due_now_count} statement/ID evidence item(s) this month to keep the pack submission-ready."
        )
        if refresh_action not in next_actions:
            readiness["next_actions"] = [refresh_action, *next_actions]
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
    uploaded_documents = await _load_user_uploaded_documents(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    filenames = _extract_document_filenames(uploaded_documents)
    matrix = build_mortgage_readiness_matrix(
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        lender_profile=request.lender_profile,
        uploaded_filenames=filenames,
    )
    return MortgageReadinessMatrixResponse(**matrix)


@app.post("/mortgage/lender-fit", response_model=MortgageLenderFitResponse)
async def evaluate_mortgage_lender_fit(
    request: MortgageLenderFitRequest,
    _user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    _validate_mortgage_selector_inputs(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        lender_profile="high_street_mainstream",
    )
    uploaded_documents = await _load_user_uploaded_documents(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    filenames = _extract_document_filenames(uploaded_documents)
    lender_fit = build_mortgage_lender_fit_snapshot(
        mortgage_type=request.mortgage_type,
        employment_profile=request.employment_profile,
        include_adverse_credit_pack=request.include_adverse_credit_pack,
        uploaded_filenames=filenames,
    )
    return MortgageLenderFitResponse(**lender_fit)


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
    uploaded_documents = await _load_user_uploaded_documents(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    filenames = _extract_document_filenames(uploaded_documents)
    pack_index = build_mortgage_pack_index(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    first_name, last_name = await _load_user_profile_name(bearer_token=bearer_token)
    quality_checks = build_mortgage_evidence_quality_checks(
        uploaded_documents=uploaded_documents,
        applicant_first_name=first_name,
        applicant_last_name=last_name,
    )
    pack_index.update(quality_checks)
    refresh_reminders = build_mortgage_refresh_reminders(uploaded_documents=uploaded_documents)
    pack_index.update(refresh_reminders)
    submission_gate = build_mortgage_submission_gate(
        readiness_status=str(pack_index.get("readiness_status", "")),
        evidence_quality_summary=quality_checks.get("evidence_quality_summary")
        if isinstance(quality_checks.get("evidence_quality_summary"), dict)
        else None,
        advisor_review_confirmed=request.advisor_review_confirmed,
    )
    pack_index["submission_gate"] = submission_gate
    quality_summary = quality_checks.get("evidence_quality_summary")
    if isinstance(quality_summary, dict) and bool(quality_summary.get("has_blockers")):
        next_actions = list(pack_index.get("next_actions", []))
        blocker_action = "Resolve critical evidence-quality blockers before broker submission."
        if blocker_action not in next_actions:
            pack_index["next_actions"] = [blocker_action, *next_actions]
    if not request.advisor_review_confirmed:
        next_actions = list(pack_index.get("next_actions", []))
        advisor_action = "Get a qualified mortgage adviser review before broker submission."
        if advisor_action not in next_actions:
            pack_index["next_actions"] = [advisor_action, *next_actions]
    refresh_summary = refresh_reminders.get("refresh_reminder_summary")
    if isinstance(refresh_summary, dict) and int(refresh_summary.get("due_now_count", 0)) > 0:
        next_actions = list(pack_index.get("next_actions", []))
        due_now_count = int(refresh_summary.get("due_now_count", 0))
        refresh_action = (
            f"Refresh {due_now_count} statement/ID evidence item(s) this month to keep the pack submission-ready."
        )
        if refresh_action not in next_actions:
            pack_index["next_actions"] = [refresh_action, *next_actions]
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
    uploaded_documents = await _load_user_uploaded_documents(
        bearer_token=bearer_token,
        max_documents_scan=request.max_documents_scan,
    )
    filenames = _extract_document_filenames(uploaded_documents)
    pack_index = build_mortgage_pack_index(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    first_name, last_name = await _load_user_profile_name(bearer_token=bearer_token)
    quality_checks = build_mortgage_evidence_quality_checks(
        uploaded_documents=uploaded_documents,
        applicant_first_name=first_name,
        applicant_last_name=last_name,
    )
    pack_index.update(quality_checks)
    refresh_reminders = build_mortgage_refresh_reminders(uploaded_documents=uploaded_documents)
    pack_index.update(refresh_reminders)
    submission_gate = build_mortgage_submission_gate(
        readiness_status=str(pack_index.get("readiness_status", "")),
        evidence_quality_summary=quality_checks.get("evidence_quality_summary")
        if isinstance(quality_checks.get("evidence_quality_summary"), dict)
        else None,
        advisor_review_confirmed=request.advisor_review_confirmed,
    )
    pack_index["submission_gate"] = submission_gate
    quality_summary = quality_checks.get("evidence_quality_summary")
    if isinstance(quality_summary, dict) and bool(quality_summary.get("has_blockers")):
        next_actions = list(pack_index.get("next_actions", []))
        blocker_action = "Resolve critical evidence-quality blockers before broker submission."
        if blocker_action not in next_actions:
            pack_index["next_actions"] = [blocker_action, *next_actions]
    if not request.advisor_review_confirmed:
        next_actions = list(pack_index.get("next_actions", []))
        advisor_action = "Get a qualified mortgage adviser review before broker submission."
        if advisor_action not in next_actions:
            pack_index["next_actions"] = [advisor_action, *next_actions]
    refresh_summary = refresh_reminders.get("refresh_reminder_summary")
    if isinstance(refresh_summary, dict) and int(refresh_summary.get("due_now_count", 0)) > 0:
        next_actions = list(pack_index.get("next_actions", []))
        due_now_count = int(refresh_summary.get("due_now_count", 0))
        refresh_action = (
            f"Refresh {due_now_count} statement/ID evidence item(s) this month to keep the pack submission-ready."
        )
        if refresh_action not in next_actions:
            pack_index["next_actions"] = [refresh_action, *next_actions]
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
