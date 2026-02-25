import os
import sys
import uuid
import datetime
import math
from collections import deque
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from .hmrc_mtd import (
    HMRCMTDQuarterlyReportSpec,
    HMRCMTDQuarterlySubmissionRequest,
    HMRCMTDQuarterlySubmissionStatus,
    build_quarterly_report_spec,
    submit_quarterly_update_to_hmrc,
)

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Integrations Service",
    description="Facades external API integrations.",
    version="1.0.0"
)
HMRC_DIRECT_API_BASE_URL = os.getenv("HMRC_DIRECT_API_BASE_URL", "https://api.service.hmrc.gov.uk")
HMRC_DIRECT_SUBMISSION_ENABLED = os.getenv("HMRC_DIRECT_SUBMISSION_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HMRC_OAUTH_TOKEN_URL = os.getenv(
    "HMRC_OAUTH_TOKEN_URL",
    "https://test-api.service.hmrc.gov.uk/oauth/token",
)
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


HMRC_DIRECT_FALLBACK_TO_SIMULATION = _parse_bool_env("HMRC_DIRECT_FALLBACK_TO_SIMULATION", False)
HMRC_OAUTH_CREDENTIALS_ROTATED_AT = os.getenv("HMRC_OAUTH_CREDENTIALS_ROTATED_AT", "").strip()
HMRC_OAUTH_ROTATION_MAX_AGE_DAYS = _parse_positive_int_env("HMRC_OAUTH_ROTATION_MAX_AGE_DAYS", 90)
HMRC_SLO_WINDOW_SIZE = _parse_positive_int_env("HMRC_SLO_WINDOW_SIZE", 200)
HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT = _parse_non_negative_float_env("HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT", 99.0)
HMRC_SLO_P95_LATENCY_TARGET_MS = _parse_non_negative_float_env("HMRC_SLO_P95_LATENCY_TARGET_MS", 2500.0)
HMRC_SUBMISSION_EVENTS: deque[dict[str, Any]] = deque(maxlen=HMRC_SLO_WINDOW_SIZE)

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


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(INTEGRATIONS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


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
        conn.commit()
        conn.close()


def reset_integrations_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
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

    return HMRCMTDOperationalReadiness(
        generated_at=datetime.datetime.now(datetime.UTC),
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


@app.get(
    "/integrations/hmrc/mtd/quarterly-update/spec",
    response_model=HMRCMTDQuarterlyReportSpec,
)
async def get_hmrc_mtd_quarterly_report_spec(
    _user_id: str = Depends(get_current_user_id),
):
    return build_quarterly_report_spec()


@app.post(
    "/integrations/hmrc/mtd/quarterly-update",
    response_model=HMRCMTDQuarterlySubmissionStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_hmrc_mtd_quarterly_update(
    request: HMRCMTDQuarterlySubmissionRequest,
    user_id: str = Depends(get_current_user_id),
):
    started_at = datetime.datetime.now(datetime.UTC)
    used_fallback = False
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
