import os
import json
import datetime
import sqlite3
import threading
import httpx
from typing import Annotated, Any, Dict, List, Optional
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, HttpUrl, Field
import uuid

# --- Configuration ---
COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")
PARTNERS_CATALOG_PATH = Path(
    os.getenv("PARTNERS_CATALOG_PATH", str(Path(__file__).with_name("partners.json")))
)
PARTNER_DB_PATH = os.getenv("PARTNER_DB_PATH", "/tmp/partner_registry.db")

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
    title="Partner Registry Service",
    description="Manages a registry of third-party partners.",
    version="1.0.0"
)

# --- Service Communication ---
async def log_audit_event(user_id: str, action: str, details: Dict[str, Any], auth_token: str) -> str | None:
    """Sends an event to the compliance service and returns the event ID."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                COMPLIANCE_SERVICE_URL,
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"user_id": user_id, "action": action, "details": details},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json().get("id")
    except httpx.RequestError as e:
        print(f"Error: Could not log audit event to compliance service: {e}")
        return None

# --- Models ---

class Partner(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: str
    services_offered: List[str]
    website: HttpUrl


class HandoffRecord(BaseModel):
    handoff_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    partner_id: uuid.UUID
    partner_name: str
    status: str = "initiated"
    audit_event_id: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

# --- Partner Catalog ---
def load_partner_catalog() -> Dict[uuid.UUID, Partner]:
    with PARTNERS_CATALOG_PATH.open("r", encoding="utf-8") as f:
        raw_partners = json.load(f)
    return {
        uuid.UUID(item["id"]): Partner(**item)
        for item in raw_partners
    }


partners_catalog = load_partner_catalog()

# --- Persistent handoff store ---
db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(PARTNER_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_partner_db() -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_handoffs (
                handoff_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                partner_id TEXT NOT NULL,
                partner_name TEXT NOT NULL,
                status TEXT NOT NULL,
                audit_event_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()


def reset_partner_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM partner_handoffs")
        conn.commit()
        conn.close()


def save_handoff(handoff: HandoffRecord) -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO partner_handoffs (
                handoff_id, user_id, partner_id, partner_name, status, audit_event_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(handoff.handoff_id),
                handoff.user_id,
                str(handoff.partner_id),
                handoff.partner_name,
                handoff.status,
                handoff.audit_event_id,
                handoff.created_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()


def list_handoffs_for_user(user_id: str) -> List[HandoffRecord]:
    with db_lock:
        conn = _connect()
        rows = conn.execute(
            """
            SELECT * FROM partner_handoffs
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        conn.close()

    return [
        HandoffRecord(
            handoff_id=uuid.UUID(row["handoff_id"]),
            user_id=row["user_id"],
            partner_id=uuid.UUID(row["partner_id"]),
            partner_name=row["partner_name"],
            status=row["status"],
            audit_event_id=row["audit_event_id"],
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
        )
        for row in rows
    ]

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/partners", response_model=List[Partner])
async def list_partners(service_type: Optional[str] = Query(None)):
    """
    Lists all available partners, optionally filtering by service type.
    """
    partners = list(partners_catalog.values())
    if service_type:
        return [
            p for p in partners if service_type in p.services_offered
        ]
    return partners

@app.get("/partners/{partner_id}", response_model=Partner)
async def get_partner_details(partner_id: uuid.UUID):
    """
    Retrieves details for a specific partner by their ID.
    """
    partner = partners_catalog.get(partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner

@app.post("/partners/{partner_id}/handoff", status_code=status.HTTP_202_ACCEPTED)
async def initiate_handoff(
    partner_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    partner = partners_catalog.get(partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    audit_event_id = await log_audit_event(
        user_id=user_id,
        action="partner.handoff.initiated",
        details={
            "partner_id": str(partner.id),
            "partner_name": partner.name,
        },
        auth_token=auth_token,
    )

    handoff = HandoffRecord(
        user_id=user_id,
        partner_id=partner.id,
        partner_name=partner.name,
        audit_event_id=audit_event_id,
    )
    save_handoff(handoff)

    return {
        "message": f"Handoff to {partner.name} initiated.",
        "audit_event_id": audit_event_id,
        "handoff_id": str(handoff.handoff_id),
    }


@app.get("/handoffs", response_model=List[HandoffRecord])
async def get_my_handoffs(user_id: str = Depends(get_current_user_id)):
    return list_handoffs_for_user(user_id)


init_partner_db()
