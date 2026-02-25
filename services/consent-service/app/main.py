from typing import Annotated, Any, Dict, List, Literal

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import uuid
import datetime
import httpx
import os
import sqlite3
import threading
import json

# --- Configuration ---
# The URL for the compliance service is now read from an environment variable.
COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")
CONSENT_DB_PATH = os.getenv("CONSENT_DB_PATH", "/tmp/consent.db")

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
    title="Consent Service",
    description="Manages user consents for data access.",
    version="1.0.0"
)

# --- Models ---

class ConsentCreate(BaseModel):
    connection_id: uuid.UUID
    provider: str
    scopes: List[str]

class Consent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    connection_id: uuid.UUID
    status: Literal['active', 'revoked'] = 'active'
    provider: str
    scopes: List[str]
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

# --- Database ---
db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(CONSENT_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_consent(row: sqlite3.Row) -> Consent:
    return Consent(
        id=uuid.UUID(row["id"]),
        user_id=row["user_id"],
        connection_id=uuid.UUID(row["connection_id"]),
        status=row["status"],
        provider=row["provider"],
        scopes=json.loads(row["scopes_json"]),
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
    )


def init_consent_db() -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                connection_id TEXT NOT NULL,
                status TEXT NOT NULL,
                provider TEXT NOT NULL,
                scopes_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()


def reset_consent_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM consents")
        conn.commit()
        conn.close()


def insert_consent_for_tests(consent: Consent) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO consents (id, user_id, connection_id, status, provider, scopes_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(consent.id),
                    consent.user_id,
                    str(consent.connection_id),
                    consent.status,
                    consent.provider,
                    json.dumps(consent.scopes),
                    consent.created_at.isoformat(),
                    consent.updated_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def create_consent(consent: Consent) -> None:
    insert_consent_for_tests(consent)


def get_consent_by_id(consent_id: uuid.UUID) -> Consent | None:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM consents WHERE id = ?", (str(consent_id),)).fetchone()
        finally:
            conn.close()
    return _row_to_consent(row) if row else None


def get_active_consents_for_user(user_id: str) -> List[Consent]:
    with db_lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT * FROM consents WHERE user_id = ? AND status = 'active'",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()
    return [_row_to_consent(row) for row in rows]


def update_consent(consent: Consent) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE consents
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (consent.status, consent.updated_at.isoformat(), str(consent.id)),
            )
            conn.commit()
        finally:
            conn.close()

# --- Service Communication ---

async def log_audit_event(user_id: str, action: str, details: Dict[str, Any], auth_token: str):
    """Sends an event to the compliance service."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                COMPLIANCE_SERVICE_URL,
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"user_id": user_id, "action": action, "details": details},
                timeout=5.0
            )
        print(f"Successfully logged audit event: {action}")
    except httpx.RequestError as e:
        # In a production system, you'd have more robust error handling,
        # like a dead-letter queue or retries with exponential backoff.
        print(f"Error: Could not log audit event to compliance service: {e}")

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/consents", response_model=Consent, status_code=status.HTTP_201_CREATED)
async def record_consent(
    consent_in: ConsentCreate,
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    """
    Records that a user has given consent for a specific connection.
    """
    new_consent = Consent(user_id=user_id, **consent_in.model_dump())
    create_consent(new_consent)

    # Log the auditable event
    await log_audit_event(
        user_id=user_id,
        action="consent.granted",
        details={
            "consent_id": str(new_consent.id),
            "provider": new_consent.provider,
            "scopes": new_consent.scopes
        },
        auth_token=auth_token,
    )

    return new_consent

@app.get("/consents", response_model=List[Consent])
async def list_active_consents(user_id: str = Depends(get_current_user_id)):
    """
    Lists all active consents for the authenticated user.
    """
    return get_active_consents_for_user(user_id)

@app.get("/consents/{consent_id}", response_model=Consent)
async def get_consent(consent_id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    """
    Retrieves a specific consent by its ID.
    """
    consent = get_consent_by_id(consent_id)
    if not consent or consent.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return consent

@app.delete("/consents/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    consent_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    """
    Revokes a user's consent.
    """
    consent = get_consent_by_id(consent_id)
    if not consent or consent.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")

    if consent.status == 'revoked':
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    consent.status = 'revoked'
    consent.updated_at = datetime.datetime.now(datetime.UTC)
    update_consent(consent)

    # Log the auditable event
    await log_audit_event(
        user_id=user_id,
        action="consent.revoked",
        details={"consent_id": str(consent.id)},
        auth_token=auth_token,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


init_consent_db()
