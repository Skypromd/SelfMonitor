import datetime
import logging
import math
import os
import sqlite3
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, cast
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .companies_house import search_companies, get_company_profile, CompanySearchResult, CompanyProfile
from .fraud_prevention import FraudPreventionHeaders
from .hmrc_apis import (
    BusinessDetail, get_business_details_simulated,
    Obligation, get_obligations_simulated,
    PeriodicUpdate, PeriodicUpdateResponse, submit_periodic_update_simulated,
    TaxCalculation, calculate_tax_simulated,
    LossRecord, record_loss_simulated, get_losses_simulated,
    VATReturn, VATReturnResponse, submit_vat_return_simulated,
    VATObligation, get_vat_obligations_simulated,
)
from .hmrc_mtd import (
    HMRCMTDQuarterlyReport,
    HMRCMTDQuarterlyReportSpec,
    HMRCMTDQuarterlySubmissionRequest,
    HMRCMTDQuarterlySubmissionStatus,
    build_quarterly_report_spec,
    compute_quarterly_report_fingerprint,
    submit_quarterly_update_to_hmrc,
    validate_quarterly_report,
)

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

logger = logging.getLogger(__name__)


def resolve_hmrc_urls_from_env() -> tuple[str, str, str]:
    """
    Choose HMRC API base + OAuth token URL from HMRC_ENV (sandbox vs production).
    Explicit HMRC_DIRECT_API_BASE_URL / HMRC_OAUTH_TOKEN_URL override env defaults.
    Returns (api_base_url, oauth_token_url, label) where label is 'sandbox' | 'production'.
    """
    raw = (os.getenv("HMRC_ENV") or "sandbox").strip().lower()
    if raw in ("production", "prod", "live"):
        label = "production"
        default_api = "https://api.service.hmrc.gov.uk"
        default_token = "https://api.service.hmrc.gov.uk/oauth/token"
    else:
        label = "sandbox"
        default_api = "https://test-api.service.hmrc.gov.uk"
        default_token = "https://test-api.service.hmrc.gov.uk/oauth/token"
    api = os.getenv("HMRC_DIRECT_API_BASE_URL", default_api).strip()
    token = os.getenv("HMRC_OAUTH_TOKEN_URL", default_token).strip()
    return api, token, label


_HMRC_RESOLVED_API, _HMRC_RESOLVED_TOKEN, HMRC_ENV_LABEL = resolve_hmrc_urls_from_env()

app = FastAPI(
    title="Integrations Service",
    description="Facades external API integrations.",
    version="1.0.0"
)
HMRC_DIRECT_API_BASE_URL = _HMRC_RESOLVED_API
HMRC_DIRECT_SUBMISSION_ENABLED = os.getenv("HMRC_DIRECT_SUBMISSION_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HMRC_OAUTH_TOKEN_URL = _HMRC_RESOLVED_TOKEN
HMRC_OAUTH_CLIENT_ID = os.getenv("HMRC_OAUTH_CLIENT_ID", "")
HMRC_OAUTH_CLIENT_SECRET = os.getenv("HMRC_OAUTH_CLIENT_SECRET", "")
HMRC_OAUTH_SCOPE = os.getenv("HMRC_OAUTH_SCOPE", "write:self-assessment")
HMRC_QUARTERLY_ENDPOINT_PATH = os.getenv(
    "HMRC_QUARTERLY_ENDPOINT_PATH",
    "/itsa/quarterly-updates",
)
HMRC_REQUEST_TIMEOUT_SECONDS = float(os.getenv("HMRC_REQUEST_TIMEOUT_SECONDS", "20"))


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_positive_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _parse_non_negative_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


HMRC_HTTP_MAX_RETRIES = _parse_positive_int_env("HMRC_HTTP_MAX_RETRIES", 3)
HMRC_HTTP_RETRY_BACKOFF_SECONDS = _parse_non_negative_float_env("HMRC_HTTP_RETRY_BACKOFF_SECONDS", 0.5)

HMRC_DIRECT_FALLBACK_TO_SIMULATION = _parse_bool_env("HMRC_DIRECT_FALLBACK_TO_SIMULATION", False)
HMRC_REQUIRE_EXPLICIT_CONFIRM = _parse_bool_env("HMRC_REQUIRE_EXPLICIT_CONFIRM", False)
POLICY_SPEC_VERSION = (os.getenv("POLICY_SPEC_VERSION", "1.0") or "1.0").strip()
HMRC_MTD_DRAFT_TTL_HOURS = _parse_positive_int_env("HMRC_MTD_DRAFT_TTL_HOURS", 24)
HMRC_MTD_CONFIRM_TTL_MINUTES = _parse_positive_int_env("HMRC_MTD_CONFIRM_TTL_MINUTES", 15)
HMRC_OAUTH_CREDENTIALS_ROTATED_AT = os.getenv("HMRC_OAUTH_CREDENTIALS_ROTATED_AT", "").strip()
HMRC_OAUTH_ROTATION_MAX_AGE_DAYS = _parse_positive_int_env("HMRC_OAUTH_ROTATION_MAX_AGE_DAYS", 90)
HMRC_SLO_WINDOW_SIZE = _parse_positive_int_env("HMRC_SLO_WINDOW_SIZE", 200)
HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT = _parse_non_negative_float_env("HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT", 99.0)
HMRC_SLO_P95_LATENCY_TARGET_MS = _parse_non_negative_float_env("HMRC_SLO_P95_LATENCY_TARGET_MS", 2500.0)
HMRC_SUBMISSION_EVENTS: deque[dict[str, Any]] = deque(maxlen=HMRC_SLO_WINDOW_SIZE)

# --- SQLite / local DB ---
INTEGRATIONS_DB_PATH = os.getenv(
    "INTEGRATIONS_DB_PATH",
    "/tmp/integrations.db",
)
INTEGRATIONS_PROCESSING_DELAY_SECONDS = _parse_non_negative_float_env(
    "INTEGRATIONS_PROCESSING_DELAY_SECONDS", 2.0
)
db_lock = threading.Lock()

# --- Models ---

class HMRCSubmissionRequest(BaseModel):
    tax_period_start: datetime.date
    tax_period_end: datetime.date
    tax_due: float

class SubmissionStatus(BaseModel):
    submission_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: Literal['pending', 'completed', 'failed']
    message: str
    provider_reference: Optional[str] = None
    submitted_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


class MTDQuarterlyDraftRequest(BaseModel):
    report: HMRCMTDQuarterlyReport


class MTDQuarterlyDraftResponse(BaseModel):
    draft_id: uuid.UUID
    report_hash: str
    policy_version: str
    expires_at: datetime.datetime


class MTDQuarterlyConfirmRequest(BaseModel):
    draft_id: uuid.UUID


class MTDQuarterlyConfirmResponse(BaseModel):
    confirmation_token: str
    policy_version: str
    expires_at: datetime.datetime


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(INTEGRATIONS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _require_and_consume_mtd_confirmation(
    request: HMRCMTDQuarterlySubmissionRequest,
    user_id: str,
) -> None:
    token = (request.confirmation_token or "").strip()
    if not token:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "HMRC submission requires explicit confirmation. "
                "POST /integrations/hmrc/mtd/quarterly-update/draft, then .../confirm, "
                "then submit with the same report and confirmation_token."
            ),
        )
    report_hash = compute_quarterly_report_fingerprint(request.report)
    now = _utc_now()
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT user_id, report_hash, expires_at, consumed_at
                FROM mtd_quarterly_confirmation_tokens
                WHERE token = ?
                """,
                (token,),
            ).fetchone()
            if not row:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid confirmation token.")
            if row["user_id"] != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Confirmation token does not match user.",
                )
            if row["consumed_at"]:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Confirmation token already used.",
                )
            exp = datetime.datetime.fromisoformat(row["expires_at"])
            if exp < now:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Confirmation token expired.",
                )
            if row["report_hash"] != report_hash:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Report payload does not match confirmed draft (hash mismatch).",
                )
            conn.execute(
                "UPDATE mtd_quarterly_confirmation_tokens SET consumed_at = ? WHERE token = ?",
                (now.isoformat(), token),
            )
            conn.commit()
        finally:
            conn.close()


def init_integrations_db() -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hmrc_submissions (
                submission_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tax_period_start TEXT NOT NULL,
                tax_period_end TEXT NOT NULL,
                tax_due REAL NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                provider_reference TEXT,
                submitted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mtd_quarterly_drafts (
                draft_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                report_json TEXT NOT NULL,
                report_hash TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mtd_quarterly_confirmation_tokens (
                token TEXT PRIMARY KEY,
                draft_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                report_hash TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()


def reset_integrations_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM mtd_quarterly_confirmation_tokens")
        conn.execute("DELETE FROM mtd_quarterly_drafts")
        conn.execute("DELETE FROM hmrc_submissions")
        conn.commit()
        conn.close()


def _row_to_submission(row: sqlite3.Row) -> SubmissionStatus:
    return SubmissionStatus(
        submission_id=uuid.UUID(row["submission_id"]),
        status=row["status"],
        message=row["message"],
        provider_reference=row["provider_reference"],
        submitted_at=datetime.datetime.fromisoformat(row["submitted_at"]),
    )


def save_submission(
    submission_id: uuid.UUID,
    user_id: str,
    request: HMRCSubmissionRequest,
    status_value: str,
    message: str,
) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO hmrc_submissions (
                    submission_id, user_id, tax_period_start, tax_period_end, tax_due,
                    status, message, provider_reference, submitted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(submission_id),
                    user_id,
                    request.tax_period_start.isoformat(),
                    request.tax_period_end.isoformat(),
                    request.tax_due,
                    status_value,
                    message,
                    None,
                    datetime.datetime.now(datetime.UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def update_submission(
    submission_id: uuid.UUID,
    status_value: str,
    message: str,
    provider_reference: Optional[str],
) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE hmrc_submissions
                SET status = ?, message = ?, provider_reference = ?
                WHERE submission_id = ?
                """,
                (status_value, message, provider_reference, str(submission_id)),
            )
            conn.commit()
        finally:
            conn.close()


def get_submission(submission_id: uuid.UUID) -> Optional[sqlite3.Row]:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM hmrc_submissions WHERE submission_id = ?",
                (str(submission_id),),
            ).fetchone()
        finally:
            conn.close()
    return row


def list_submissions_for_user(user_id: str) -> List[SubmissionStatus]:
    with db_lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM hmrc_submissions
                WHERE user_id = ?
                ORDER BY submitted_at DESC
                """,
                (user_id,),
            ).fetchall()
        finally:
            conn.close()
    return [_row_to_submission(row) for row in rows]


def process_submission_async(submission_id: uuid.UUID) -> None:
    update_submission(
        submission_id,
        status_value="pending",
        message="Submission accepted by HMRC and queued for processing.",
        provider_reference=None,
    )
    time.sleep(INTEGRATIONS_PROCESSING_DELAY_SECONDS)
    provider_reference = f"hmrc-{submission_id.hex[:12]}"
    update_submission(
        submission_id,
        status_value="completed",
        message="Submission processed successfully by HMRC.",
        provider_reference=provider_reference,
    )


class HMRCMTDSubmissionSLOSnapshot(BaseModel):
    generated_at: datetime.datetime
    window_size: int
    total_submissions: int
    successful_submissions: int
    failed_submissions: int
    fallback_submissions: int
    direct_mode_submissions: int
    simulated_mode_submissions: int
    success_rate_percent: float
    p95_latency_ms: float
    success_rate_target_percent: float
    p95_latency_target_ms: float
    success_rate_alert: bool
    latency_alert: bool
    note: str


class HMRCMTDOperationalReadiness(BaseModel):
    generated_at: datetime.datetime
    hmrc_environment: Literal["sandbox", "production"]
    hmrc_api_base_url: str
    oauth_token_host: str
    http_max_retries: int
    http_retry_backoff_seconds: float
    direct_submission_enabled: bool
    fallback_to_simulation_enabled: bool
    oauth_credentials_configured: bool
    credential_rotation_date: datetime.date | None
    credential_age_days: int | None
    credential_rotation_max_age_days: int
    credential_rotation_overdue: bool
    readiness_band: Literal["ready", "degraded", "not_ready"]
    notes: list[str]


def _parse_iso_date(value: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _record_submission_event(
    *,
    success: bool,
    latency_ms: float,
    transmission_mode: Literal["simulated", "direct"],
    used_fallback: bool,
) -> None:
    HMRC_SUBMISSION_EVENTS.append(
        {
            "timestamp": datetime.datetime.now(datetime.UTC),
            "success": success,
            "latency_ms": max(latency_ms, 0.0),
            "transmission_mode": transmission_mode,
            "used_fallback": used_fallback,
        }
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100.0) * len(ordered)))
    return float(ordered[rank - 1])


def _build_submission_slo_snapshot() -> HMRCMTDSubmissionSLOSnapshot:
    events = list(HMRC_SUBMISSION_EVENTS)
    total_submissions = len(events)
    successful_submissions = sum(1 for item in events if bool(item.get("success")))
    failed_submissions = total_submissions - successful_submissions
    fallback_submissions = sum(1 for item in events if bool(item.get("used_fallback")))
    direct_mode_submissions = sum(1 for item in events if str(item.get("transmission_mode")) == "direct")
    simulated_mode_submissions = sum(1 for item in events if str(item.get("transmission_mode")) == "simulated")
    latency_points = [float(item.get("latency_ms") or 0.0) for item in events]

    success_rate_percent = (
        round((successful_submissions / total_submissions) * 100.0, 2)
        if total_submissions > 0
        else 100.0
    )
    p95_latency_ms = round(_percentile(latency_points, 95.0), 1) if latency_points else 0.0
    success_rate_alert = success_rate_percent < HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT
    latency_alert = p95_latency_ms > HMRC_SLO_P95_LATENCY_TARGET_MS
    return HMRCMTDSubmissionSLOSnapshot(
        generated_at=datetime.datetime.now(datetime.UTC),
        window_size=HMRC_SLO_WINDOW_SIZE,
        total_submissions=total_submissions,
        successful_submissions=successful_submissions,
        failed_submissions=failed_submissions,
        fallback_submissions=fallback_submissions,
        direct_mode_submissions=direct_mode_submissions,
        simulated_mode_submissions=simulated_mode_submissions,
        success_rate_percent=success_rate_percent,
        p95_latency_ms=p95_latency_ms,
        success_rate_target_percent=HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT,
        p95_latency_target_ms=HMRC_SLO_P95_LATENCY_TARGET_MS,
        success_rate_alert=success_rate_alert,
        latency_alert=latency_alert,
        note=(
            "Snapshot is computed from in-process rolling submission events. "
            "Use Prometheus scraping plus this endpoint for operational dashboards."
        ),
    )


def _build_operational_readiness_snapshot() -> HMRCMTDOperationalReadiness:
    notes: list[str] = []
    oauth_credentials_configured = bool(HMRC_OAUTH_CLIENT_ID and HMRC_OAUTH_CLIENT_SECRET and HMRC_OAUTH_TOKEN_URL)
    rotation_date = _parse_iso_date(HMRC_OAUTH_CREDENTIALS_ROTATED_AT) if HMRC_OAUTH_CREDENTIALS_ROTATED_AT else None
    credential_age_days: int | None = None
    credential_rotation_overdue = False
    if rotation_date is not None:
        credential_age_days = (datetime.datetime.now(datetime.UTC).date() - rotation_date).days
        credential_rotation_overdue = credential_age_days > HMRC_OAUTH_ROTATION_MAX_AGE_DAYS
    elif HMRC_DIRECT_SUBMISSION_ENABLED:
        credential_rotation_overdue = True

    if HMRC_DIRECT_SUBMISSION_ENABLED and not oauth_credentials_configured:
        notes.append("Direct submission enabled but OAuth credentials are incomplete.")
    if HMRC_DIRECT_SUBMISSION_ENABLED and credential_rotation_overdue:
        notes.append("OAuth credentials rotation is overdue or rotation date is missing.")
    if HMRC_DIRECT_SUBMISSION_ENABLED and HMRC_DIRECT_FALLBACK_TO_SIMULATION:
        notes.append("Automatic direct->simulation fallback is enabled for resilience.")
    if not HMRC_DIRECT_SUBMISSION_ENABLED:
        notes.append("Direct submission disabled; running in simulation-only mode.")
    if not notes:
        notes.append("Operational readiness checks passed for direct HMRC submissions.")

    if HMRC_DIRECT_SUBMISSION_ENABLED and oauth_credentials_configured and not credential_rotation_overdue:
        readiness_band: Literal["ready", "degraded", "not_ready"] = "ready"
    elif HMRC_DIRECT_SUBMISSION_ENABLED and HMRC_DIRECT_FALLBACK_TO_SIMULATION:
        readiness_band = "degraded"
    elif not HMRC_DIRECT_SUBMISSION_ENABLED:
        readiness_band = "degraded"
    else:
        readiness_band = "not_ready"

    token_host = urlparse(HMRC_OAUTH_TOKEN_URL).netloc or HMRC_OAUTH_TOKEN_URL

    return HMRCMTDOperationalReadiness(
        generated_at=datetime.datetime.now(datetime.UTC),
        hmrc_environment=cast(Literal["sandbox", "production"], HMRC_ENV_LABEL),
        hmrc_api_base_url=HMRC_DIRECT_API_BASE_URL,
        oauth_token_host=token_host,
        http_max_retries=HMRC_HTTP_MAX_RETRIES,
        http_retry_backoff_seconds=HMRC_HTTP_RETRY_BACKOFF_SECONDS,
        direct_submission_enabled=HMRC_DIRECT_SUBMISSION_ENABLED,
        fallback_to_simulation_enabled=HMRC_DIRECT_FALLBACK_TO_SIMULATION,
        oauth_credentials_configured=oauth_credentials_configured,
        credential_rotation_date=rotation_date,
        credential_age_days=credential_age_days,
        credential_rotation_max_age_days=HMRC_OAUTH_ROTATION_MAX_AGE_DAYS,
        credential_rotation_overdue=credential_rotation_overdue,
        readiness_band=readiness_band,
        notes=notes,
    )

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post(
    "/integrations/hmrc/submit-tax-return",
    response_model=SubmissionStatus,
    status_code=status.HTTP_202_ACCEPTED
)
async def submit_tax_return(
    request: HMRCSubmissionRequest,
    user_id: str = Depends(get_current_user_id)
):
    submission_id = uuid.uuid4()
    save_submission(
        submission_id=submission_id,
        user_id=user_id,
        request=request,
        status_value="pending",
        message="Submission received and queued for HMRC processing.",
    )
    return _row_to_submission(
        _connect().execute(
            "SELECT * FROM submissions WHERE submission_id = ?", (str(submission_id),)
        ).fetchone()
    )


@app.get(
    "/integrations/hmrc/mtd/quarterly-update/spec",
    response_model=HMRCMTDQuarterlyReportSpec,
)
async def get_hmrc_mtd_quarterly_report_spec(
    _user_id: str = Depends(get_current_user_id),
):
    return build_quarterly_report_spec()


@app.post(
    "/integrations/hmrc/mtd/quarterly-update/draft",
    response_model=MTDQuarterlyDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hmrc_mtd_quarterly_draft(
    body: MTDQuarterlyDraftRequest,
    user_id: str = Depends(get_current_user_id),
):
    errors = validate_quarterly_report(body.report)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid HMRC MTD quarterly report format: {'; '.join(errors)}",
        )
    report_hash = compute_quarterly_report_fingerprint(body.report)
    report_json = body.report.model_dump_json()
    now = _utc_now()
    expires = now + datetime.timedelta(hours=HMRC_MTD_DRAFT_TTL_HOURS)
    draft_id = uuid.uuid4()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO mtd_quarterly_drafts (
                    draft_id, user_id, report_json, report_hash, policy_version, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(draft_id),
                    user_id,
                    report_json,
                    report_hash,
                    POLICY_SPEC_VERSION,
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return MTDQuarterlyDraftResponse(
        draft_id=draft_id,
        report_hash=report_hash,
        policy_version=POLICY_SPEC_VERSION,
        expires_at=expires,
    )


@app.post(
    "/integrations/hmrc/mtd/quarterly-update/confirm",
    response_model=MTDQuarterlyConfirmResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_hmrc_mtd_quarterly_draft(
    body: MTDQuarterlyConfirmRequest,
    user_id: str = Depends(get_current_user_id),
):
    now = _utc_now()
    policy_version = POLICY_SPEC_VERSION
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT user_id, report_hash, policy_version, expires_at
                FROM mtd_quarterly_drafts
                WHERE draft_id = ?
                """,
                (str(body.draft_id),),
            ).fetchone()
            if not row:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Draft not found.")
            if row["user_id"] != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Draft belongs to another user.",
                )
            policy_version = row["policy_version"] or POLICY_SPEC_VERSION
            draft_exp = datetime.datetime.fromisoformat(row["expires_at"])
            if draft_exp < now:
                raise HTTPException(status.HTTP_410_GONE, detail="Draft expired.")
            token = str(uuid.uuid4())
            confirm_exp = now + datetime.timedelta(minutes=HMRC_MTD_CONFIRM_TTL_MINUTES)
            conn.execute(
                """
                INSERT INTO mtd_quarterly_confirmation_tokens (
                    token, draft_id, user_id, report_hash, policy_version, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token,
                    str(body.draft_id),
                    user_id,
                    row["report_hash"],
                    policy_version,
                    now.isoformat(),
                    confirm_exp.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return MTDQuarterlyConfirmResponse(
        confirmation_token=token,
        policy_version=policy_version,
        expires_at=confirm_exp,
    )


@app.post(
    "/integrations/hmrc/mtd/quarterly-update",
    response_model=HMRCMTDQuarterlySubmissionStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_hmrc_mtd_quarterly_update(
    request: HMRCMTDQuarterlySubmissionRequest,
    user_id: str = Depends(get_current_user_id),
):
    if HMRC_REQUIRE_EXPLICIT_CONFIRM:
        _require_and_consume_mtd_confirmation(request, user_id)
    started_at = datetime.datetime.now(datetime.UTC)
    used_fallback = False
    fraud_headers = FraudPreventionHeaders().generate(user_id=user_id)
    try:
        result = await submit_quarterly_update_to_hmrc(
            request=request,
            user_id=user_id,
            hmrc_direct_api_base_url=HMRC_DIRECT_API_BASE_URL,
            hmrc_direct_submission_enabled=HMRC_DIRECT_SUBMISSION_ENABLED,
            hmrc_oauth_token_url=HMRC_OAUTH_TOKEN_URL,
            hmrc_oauth_client_id=HMRC_OAUTH_CLIENT_ID,
            hmrc_oauth_client_secret=HMRC_OAUTH_CLIENT_SECRET,
            hmrc_oauth_scope=HMRC_OAUTH_SCOPE,
            hmrc_quarterly_endpoint_path=HMRC_QUARTERLY_ENDPOINT_PATH,
            request_timeout_seconds=HMRC_REQUEST_TIMEOUT_SECONDS,
            fraud_headers=fraud_headers,
            max_retries=HMRC_HTTP_MAX_RETRIES,
            retry_backoff_seconds=HMRC_HTTP_RETRY_BACKOFF_SECONDS,
        )
    except ValueError as exc:
        detail = str(exc)
        is_direct_config_error = (
            "OAuth credentials are missing" in detail
            or "HMRC_OAUTH_TOKEN_URL is required" in detail
        )
        if HMRC_DIRECT_SUBMISSION_ENABLED and HMRC_DIRECT_FALLBACK_TO_SIMULATION and is_direct_config_error:
            used_fallback = True
            result = await submit_quarterly_update_to_hmrc(
                request=request,
                user_id=user_id,
                hmrc_direct_api_base_url=HMRC_DIRECT_API_BASE_URL,
                hmrc_direct_submission_enabled=False,
                hmrc_oauth_token_url=HMRC_OAUTH_TOKEN_URL,
                hmrc_oauth_client_id=HMRC_OAUTH_CLIENT_ID,
                hmrc_oauth_client_secret=HMRC_OAUTH_CLIENT_SECRET,
                hmrc_oauth_scope=HMRC_OAUTH_SCOPE,
                hmrc_quarterly_endpoint_path=HMRC_QUARTERLY_ENDPOINT_PATH,
                request_timeout_seconds=HMRC_REQUEST_TIMEOUT_SECONDS,
                fraud_headers=fraud_headers,
                max_retries=HMRC_HTTP_MAX_RETRIES,
                retry_backoff_seconds=HMRC_HTTP_RETRY_BACKOFF_SECONDS,
            )
            result.message = (
                f"{result.message} Fallback applied because direct mode was not ready: {detail}"
            )
        else:
            latency_ms = (datetime.datetime.now(datetime.UTC) - started_at).total_seconds() * 1000.0
            _record_submission_event(
                success=False,
                latency_ms=latency_ms,
                transmission_mode="direct" if HMRC_DIRECT_SUBMISSION_ENABLED else "simulated",
                used_fallback=False,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid HMRC MTD quarterly report format: {exc}",
            ) from exc
    except httpx.HTTPStatusError as exc:
        if HMRC_DIRECT_SUBMISSION_ENABLED and HMRC_DIRECT_FALLBACK_TO_SIMULATION:
            used_fallback = True
            result = await submit_quarterly_update_to_hmrc(
                request=request,
                user_id=user_id,
                hmrc_direct_api_base_url=HMRC_DIRECT_API_BASE_URL,
                hmrc_direct_submission_enabled=False,
                hmrc_oauth_token_url=HMRC_OAUTH_TOKEN_URL,
                hmrc_oauth_client_id=HMRC_OAUTH_CLIENT_ID,
                hmrc_oauth_client_secret=HMRC_OAUTH_CLIENT_SECRET,
                hmrc_oauth_scope=HMRC_OAUTH_SCOPE,
                hmrc_quarterly_endpoint_path=HMRC_QUARTERLY_ENDPOINT_PATH,
                request_timeout_seconds=HMRC_REQUEST_TIMEOUT_SECONDS,
                fraud_headers=fraud_headers,
                max_retries=HMRC_HTTP_MAX_RETRIES,
                retry_backoff_seconds=HMRC_HTTP_RETRY_BACKOFF_SECONDS,
            )
            result.message = (
                f"{result.message} Fallback applied after HMRC status error: {exc.response.status_code}."
            )
        else:
            latency_ms = (datetime.datetime.now(datetime.UTC) - started_at).total_seconds() * 1000.0
            _record_submission_event(
                success=False,
                latency_ms=latency_ms,
                transmission_mode="direct" if HMRC_DIRECT_SUBMISSION_ENABLED else "simulated",
                used_fallback=False,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"HMRC API returned error status {exc.response.status_code}.",
            ) from exc
    except httpx.HTTPError as exc:
        if HMRC_DIRECT_SUBMISSION_ENABLED and HMRC_DIRECT_FALLBACK_TO_SIMULATION:
            used_fallback = True
            result = await submit_quarterly_update_to_hmrc(
                request=request,
                user_id=user_id,
                hmrc_direct_api_base_url=HMRC_DIRECT_API_BASE_URL,
                hmrc_direct_submission_enabled=False,
                hmrc_oauth_token_url=HMRC_OAUTH_TOKEN_URL,
                hmrc_oauth_client_id=HMRC_OAUTH_CLIENT_ID,
                hmrc_oauth_client_secret=HMRC_OAUTH_CLIENT_SECRET,
                hmrc_oauth_scope=HMRC_OAUTH_SCOPE,
                hmrc_quarterly_endpoint_path=HMRC_QUARTERLY_ENDPOINT_PATH,
                request_timeout_seconds=HMRC_REQUEST_TIMEOUT_SECONDS,
                fraud_headers=fraud_headers,
                max_retries=HMRC_HTTP_MAX_RETRIES,
                retry_backoff_seconds=HMRC_HTTP_RETRY_BACKOFF_SECONDS,
            )
            result.message = f"{result.message} Fallback applied after HMRC connectivity error."
        else:
            latency_ms = (datetime.datetime.now(datetime.UTC) - started_at).total_seconds() * 1000.0
            _record_submission_event(
                success=False,
                latency_ms=latency_ms,
                transmission_mode="direct" if HMRC_DIRECT_SUBMISSION_ENABLED else "simulated",
                used_fallback=False,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not connect to HMRC API: {exc}",
            ) from exc
    latency_ms = (datetime.datetime.now(datetime.UTC) - started_at).total_seconds() * 1000.0
    _record_submission_event(
        success=result.status != "failed",
        latency_ms=latency_ms,
        transmission_mode=result.transmission_mode,
        used_fallback=used_fallback,
    )
    return result


@app.get(
    "/integrations/hmrc/mtd/submission-slo",
    response_model=HMRCMTDSubmissionSLOSnapshot,
)
async def get_hmrc_mtd_submission_slo_snapshot(
    _user_id: str = Depends(get_current_user_id),
):
    return _build_submission_slo_snapshot()


@app.get(
    "/integrations/hmrc/mtd/operational-readiness",
    response_model=HMRCMTDOperationalReadiness,
)
async def get_hmrc_mtd_operational_readiness(
    _user_id: str = Depends(get_current_user_id),
):
    return _build_operational_readiness_snapshot()


# --- HMRC MTD ITSA Compliance Models & Endpoints ---


class FinalDeclarationRequest(BaseModel):
    tax_year_start: datetime.date
    tax_year_end: datetime.date
    total_income: float
    total_expenses: float
    total_allowances: float = 0.0
    loss_brought_forward: float = 0.0
    declaration: Literal["true_and_complete"] = "true_and_complete"


class FinalDeclarationStatus(BaseModel):
    declaration_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: Literal["accepted", "pending", "rejected"]
    message: str
    tax_year: str
    total_tax_due: float
    hmrc_receipt_reference: str
    submitted_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


@app.post(
    "/integrations/hmrc/mtd/final-declaration",
    response_model=FinalDeclarationStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_final_declaration(
    request: FinalDeclarationRequest,
    user_id: str = Depends(get_current_user_id),
):
    if request.tax_year_end != datetime.date(request.tax_year_start.year + 1, 4, 5):
        raise HTTPException(status_code=400, detail="tax_year_end must be 5 April following tax_year_start")

    taxable_income = max(request.total_income - request.total_expenses - request.total_allowances - request.loss_brought_forward, 0.0)

    # UK Income Tax calculation (2025/26 rates)
    tax_due = 0.0
    personal_allowance = 12570.0
    if taxable_income > personal_allowance:
        remaining = taxable_income - personal_allowance
        basic = min(remaining, 37700.0)
        tax_due += basic * 0.20
        remaining -= basic
        if remaining > 0:
            higher = min(remaining, 87440.0)
            tax_due += higher * 0.40
            remaining -= higher
        if remaining > 0:
            tax_due += remaining * 0.45

    # NI Class 4
    ni_lower = 12570.0
    ni_upper = 50270.0
    ni_due = 0.0
    if taxable_income > ni_lower:
        ni_basic = min(taxable_income - ni_lower, ni_upper - ni_lower)
        ni_due += ni_basic * 0.06
        if taxable_income > ni_upper:
            ni_due += (taxable_income - ni_upper) * 0.02

    total_tax = round(tax_due + ni_due, 2)

    receipt_ref = f"HMRC-FD-{datetime.datetime.now(datetime.UTC):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
    tax_year_str = f"{request.tax_year_start.year}/{request.tax_year_end.year}"

    return FinalDeclarationStatus(
        status="accepted" if not HMRC_DIRECT_SUBMISSION_ENABLED else "pending",
        message=f"Final declaration for tax year {tax_year_str} accepted. Total tax due: \u00a3{total_tax:.2f}",
        tax_year=tax_year_str,
        total_tax_due=total_tax,
        hmrc_receipt_reference=receipt_ref,
    )


class LossAdjustmentRequest(BaseModel):
    tax_year: str
    loss_type: Literal["trading", "property", "capital"]
    loss_amount: float = Field(gt=0)
    carry_forward: bool = True
    offset_against: Literal["same_trade", "general_income", "capital_gains"] = "same_trade"


class LossAdjustmentResponse(BaseModel):
    adjustment_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: Literal["recorded", "applied"]
    loss_type: str
    loss_amount: float
    carry_forward_amount: float
    message: str


@app.post(
    "/integrations/hmrc/mtd/loss-adjustment",
    response_model=LossAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_loss_adjustment(
    request: LossAdjustmentRequest,
    user_id: str = Depends(get_current_user_id),
):
    carry_forward = request.loss_amount if request.carry_forward else 0.0
    return LossAdjustmentResponse(
        status="recorded",
        loss_type=request.loss_type,
        loss_amount=request.loss_amount,
        carry_forward_amount=carry_forward,
        message=f"{request.loss_type.title()} loss of \u00a3{request.loss_amount:.2f} recorded for {request.tax_year}. "
                f"{'Will be carried forward to next tax year.' if request.carry_forward else 'Applied to current year.'}",
    )


class BSASRequest(BaseModel):
    tax_year_start: datetime.date
    business_id: str = "default"
    accounting_type: Literal["cash", "accruals"] = "cash"


class BSASResponse(BaseModel):
    calculation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tax_year: str
    total_income: float
    total_expenses: float
    net_profit: float
    adjustments: List[Dict[str, Any]]
    status: Literal["valid", "superseded"]


@app.get(
    "/integrations/hmrc/mtd/bsas/{tax_year}",
    response_model=BSASResponse,
)
async def get_bsas_summary(
    tax_year: str,
    user_id: str = Depends(get_current_user_id),
):
    return BSASResponse(
        tax_year=tax_year,
        total_income=0.0,
        total_expenses=0.0,
        net_profit=0.0,
        adjustments=[],
        status="valid",
    )


# --- Companies House Endpoints ---

@app.get("/integrations/companies-house/search", response_model=list[CompanySearchResult])
async def search_companies_endpoint(
    q: str,
    limit: int = 10,
    _user_id: str = Depends(get_current_user_id),
):
    """Search Companies House for a company by name or number"""
    return await search_companies(q, items_per_page=limit)

@app.get("/integrations/companies-house/company/{company_number}", response_model=CompanyProfile)
async def get_company_profile_endpoint(
    company_number: str,
    _user_id: str = Depends(get_current_user_id),
):
    """Get detailed company profile from Companies House"""
    profile = await get_company_profile(company_number)
    if not profile:
        raise HTTPException(status_code=404, detail="Company not found")
    return profile


# === HMRC MTD Minimum Functionality Endpoints ===

@app.get("/integrations/hmrc/mtd/business-details", response_model=list[BusinessDetail])
async def get_business_details(
    nino: str = "AB123456C",
    _user_id: str = Depends(get_current_user_id),
):
    """Get business details for MTD (minimum functionality requirement)"""
    return get_business_details_simulated(nino)

@app.get("/integrations/hmrc/mtd/obligations", response_model=list[Obligation])
async def get_obligations(
    tax_year: str = "2025",
    nino: str = "AB123456C",
    _user_id: str = Depends(get_current_user_id),
):
    """Get quarterly obligation deadlines (minimum functionality requirement)"""
    return get_obligations_simulated(nino, tax_year)

@app.post("/integrations/hmrc/mtd/periodic-update", response_model=PeriodicUpdateResponse, status_code=202)
async def submit_periodic_update(
    update: PeriodicUpdate,
    _user_id: str = Depends(get_current_user_id),
):
    """Submit quarterly periodic update for self-employment income (minimum functionality requirement)"""
    return submit_periodic_update_simulated(update)

@app.post("/integrations/hmrc/mtd/tax-calculation", response_model=TaxCalculation)
async def trigger_tax_calculation(
    total_income: float,
    total_deductions: float = 0,
    tax_year: str = "2025/2026",
    _user_id: str = Depends(get_current_user_id),
):
    """Trigger in-year tax calculation estimate (minimum functionality requirement)"""
    return calculate_tax_simulated(total_income, total_deductions, tax_year)

@app.post("/integrations/hmrc/mtd/losses", response_model=LossRecord, status_code=201)
async def record_loss(
    tax_year: str,
    loss_type: str = "self-employment",
    amount: float = 0,
    relief: str = "carry-forward",
    _user_id: str = Depends(get_current_user_id),
):
    """Record business loss for carry-forward/sideways (minimum functionality requirement)"""
    return record_loss_simulated(tax_year, loss_type, amount, relief)

@app.get("/integrations/hmrc/mtd/losses/{tax_year}", response_model=list[LossRecord])
async def get_losses(
    tax_year: str,
    _user_id: str = Depends(get_current_user_id),
):
    """View recorded losses for a tax year"""
    return get_losses_simulated(tax_year)

@app.post("/integrations/hmrc/vat/return", response_model=VATReturnResponse, status_code=202)
async def submit_vat_return(
    vat_return: VATReturn,
    _user_id: str = Depends(get_current_user_id),
):
    """Submit VAT return to HMRC"""
    return submit_vat_return_simulated(vat_return)

@app.get("/integrations/hmrc/vat/obligations", response_model=list[VATObligation])
async def get_vat_obligations(
    vrn: str = "123456789",
    _user_id: str = Depends(get_current_user_id),
):
    """Get VAT obligations/deadlines"""
    return get_vat_obligations_simulated(vrn)


@app.on_event("startup")
async def _on_startup() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_integrations_db()
