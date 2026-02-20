import os
import json
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

# --- Partner Catalog ---
def load_partner_catalog() -> Dict[uuid.UUID, Partner]:
    with PARTNERS_CATALOG_PATH.open("r", encoding="utf-8") as f:
        raw_partners = json.load(f)
    return {
        uuid.UUID(item["id"]): Partner(**item)
        for item in raw_partners
    }


partners_catalog = load_partner_catalog()

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
    """
    Initiates a user handoff to a partner and records it as a compliance event.
    """
    partner = partners_catalog.get(partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    # In a real app, this would trigger a workflow: e.g., send an email,
    # make an API call to the partner's system, etc.
    print(f"Initiating handoff for user {user_id} to partner {partner.name}.")

    audit_event_id = await log_audit_event(
        user_id=user_id,
        action="partner.handoff.initiated",
        details={
            "partner_id": str(partner.id),
            "partner_name": partner.name,
        },
        auth_token=auth_token,
    )

    return {
        "message": f"Handoff to {partner.name} initiated.",
        "audit_event_id": audit_event_id
    }
