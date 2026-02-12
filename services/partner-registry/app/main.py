import os
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from jose import JWTError, jwt
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
import uuid

# --- Configuration ---
COMPLIANCE_SERVICE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8003/audit-events")
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"

def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    return authorization.split(" ", 1)[1]


def get_current_user_id(token: str = Depends(get_bearer_token)) -> str:
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    return user_id

app = FastAPI(
    title="Partner Registry Service",
    description="Manages a registry of third-party partners.",
    version="1.0.0"
)

# --- Service Communication ---
async def log_audit_event(user_id: str, action: str, details: Dict[str, Any]) -> str | None:
    """Sends an event to the compliance service and returns the event ID."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                COMPLIANCE_SERVICE_URL,
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

# --- "Database" ---

# In-memory partner store for demonstration purposes
fake_partners_db = {
    uuid.UUID("1a8a8f69-a1b7-4c13-9a16-9e9f9a2e3f5d"): Partner(
        id=uuid.UUID("1a8a8f69-a1b7-4c13-9a16-9e9f9a2e3f5d"),
        name="SafeFuture Financial Advisors",
        description="Independent financial advisors regulated by the FCA.",
        services_offered=["pension_advice", "investment_management", "income_protection"],
        website="https://www.safefuture.example.com"
    ),
    uuid.UUID("b4f1f2d5-9c9a-4e1e-b8d4-5b4d7f6c3a1b"): Partner(
        id=uuid.UUID("b4f1f2d5-9c9a-4e1e-b8d4-5b4d7f6c3a1b"),
        name="HomePath Mortgages",
        description="Specialist mortgage brokers for first-time buyers.",
        services_offered=["mortgage_advice"],
        website="https://www.homepath.example.com"
    ),
    uuid.UUID("c5e3e1d4-8d8a-3d0d-a7c3-4c3d6f5b2a0a"): Partner(
        id=uuid.UUID("c5e3e1d4-8d8a-3d0d-a7c3-4c3d6f5b2a0a"),
        name="TaxSolve Accountants",
        description="Chartered accountants specializing in self-assessment for freelancers.",
        services_offered=["accounting", "tax_filing"],
        website="https://www.taxsolve.example.com"
    )
}

# --- Endpoints ---

@app.get("/partners", response_model=List[Partner])
async def list_partners(service_type: Optional[str] = Query(None)):
    """
    Lists all available partners, optionally filtering by service type.
    """
    partners = list(fake_partners_db.values())
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
    partner = fake_partners_db.get(partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner

@app.post("/partners/{partner_id}/handoff", status_code=status.HTTP_202_ACCEPTED)
async def initiate_handoff(
    partner_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id)
):
    """
    Initiates a user handoff to a partner and records it as a compliance event.
    """
    partner = fake_partners_db.get(partner_id)
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
        }
    )

    return {
        "message": f"Handoff to {partner.name} initiated.",
        "audit_event_id": audit_event_id
    }
