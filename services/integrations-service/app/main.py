import datetime
import os
import sqlite3
import threading
import time
import uuid
from typing import Annotated, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
INTEGRATIONS_DB_PATH = os.getenv("INTEGRATIONS_DB_PATH", "/tmp/integrations.db")
INTEGRATIONS_PROCESSING_DELAY_SECONDS = float(os.getenv("INTEGRATIONS_PROCESSING_DELAY_SECONDS", "0.25"))
db_lock = threading.Lock()


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
    title="Integrations Service",
    description="Facades external API integrations.",
    version="1.0.0"
)

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
        conn.close()


def update_submission(
    submission_id: uuid.UUID,
    status_value: str,
    message: str,
    provider_reference: Optional[str],
) -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            UPDATE hmrc_submissions
            SET status = ?, message = ?, provider_reference = ?
            WHERE submission_id = ?
            """,
            (status_value, message, provider_reference, str(submission_id)),
        )
        conn.commit()
        conn.close()


def get_submission(submission_id: uuid.UUID) -> Optional[sqlite3.Row]:
    with db_lock:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM hmrc_submissions WHERE submission_id = ?",
            (str(submission_id),),
        ).fetchone()
        conn.close()
    return row


def list_submissions_for_user(user_id: str) -> List[SubmissionStatus]:
    with db_lock:
        conn = _connect()
        rows = conn.execute(
            """
            SELECT * FROM hmrc_submissions
            WHERE user_id = ?
            ORDER BY submitted_at DESC
            """,
            (user_id,),
        ).fetchall()
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
    threading.Thread(target=process_submission_async, args=(submission_id,), daemon=True).start()
    row = get_submission(submission_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist submission")
    return _row_to_submission(row)


@app.get(
    "/integrations/hmrc/submissions/{submission_id}",
    response_model=SubmissionStatus,
)
async def get_hmrc_submission_status(
    submission_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
):
    row = get_submission(submission_id)
    if row is None or row["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return _row_to_submission(row)


@app.get(
    "/integrations/hmrc/submissions",
    response_model=List[SubmissionStatus],
)
async def list_my_hmrc_submissions(user_id: str = Depends(get_current_user_id)):
    return list_submissions_for_user(user_id)


init_integrations_db()
