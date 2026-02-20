from typing import Annotated, Any, Dict, List, Literal

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import uuid
import datetime
import httpx
import os

# --- Configuration ---
# The URL for the compliance service is now read from an environment variable.
COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")

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

# --- "Database" ---

# In-memory consent store for demonstration purposes
# Keyed by consent_id
fake_consents_db: Dict[uuid.UUID, Consent] = {}

# --- Service Communication ---

async def log_audit_event(user_id: str, action: str, details: Dict[str, Any]):
    """Sends an event to the compliance service."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                COMPLIANCE_SERVICE_URL,
                json={"user_id": user_id, "action": action, "details": details},
                timeout=5.0
            )
        print(f"Successfully logged audit event: {action}")
    except httpx.RequestError as e:
        # In a production system, you'd have more robust error handling,
        # like a dead-letter queue or retries with exponential backoff.
        print(f"Error: Could not log audit event to compliance service: {e}")

# --- Endpoints ---

@app.post("/consents", response_model=Consent, status_code=status.HTTP_201_CREATED)
async def record_consent(consent_in: ConsentCreate, user_id: str = Depends(get_current_user_id)):
    """
    Records that a user has given consent for a specific connection.
    """
    new_consent = Consent(user_id=user_id, **consent_in.model_dump())
    fake_consents_db[new_consent.id] = new_consent

    # Log the auditable event
    await log_audit_event(
        user_id=user_id,
        action="consent.granted",
        details={
            "consent_id": str(new_consent.id),
            "provider": new_consent.provider,
            "scopes": new_consent.scopes
        }
    )

    return new_consent

@app.get("/consents", response_model=List[Consent])
async def list_active_consents(user_id: str = Depends(get_current_user_id)):
    """
    Lists all active consents for the authenticated user.
    """
    user_consents = [
        c for c in fake_consents_db.values() 
        if c.user_id == user_id and c.status == 'active'
    ]
    return user_consents

@app.get("/consents/{consent_id}", response_model=Consent)
async def get_consent(consent_id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    """
    Retrieves a specific consent by its ID.
    """
    consent = fake_consents_db.get(consent_id)
    if not consent or consent.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return consent

@app.delete("/consents/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(consent_id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    """
    Revokes a user's consent.
    """
    consent = fake_consents_db.get(consent_id)
    if not consent or consent.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")

    if consent.status == 'revoked':
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    consent.status = 'revoked'
    consent.updated_at = datetime.datetime.now(datetime.UTC)

    # Log the auditable event
    await log_audit_event(
        user_id=user_id,
        action="consent.revoked",
        details={"consent_id": str(consent.id)}
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
