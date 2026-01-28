from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uuid
import datetime
import os
import hvac
from .celery_app import import_transactions_task
from .providers import get_provider, list_providers

# --- Vault Client Setup ---
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")

vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
if vault_client.is_authenticated():
    print("Successfully authenticated with Vault.")
else:
    print("Error: Could not authenticate with Vault.")


def save_connection_metadata(connection_id: str, metadata: dict):
    """Saves provider metadata to Vault."""
    secret_path = f"kv/banking-connections/{connection_id}"
    try:
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=secret_path,
            secret=metadata,
        )
        print(f"Metadata for connection {connection_id} securely stored in Vault.")
    except Exception as e:
        print(f"Error storing tokens in Vault: {e}")


# --- Placeholder Security ---
def fake_auth_check():
    """A fake dependency to simulate user authentication."""
    return {"user_id": "fake-user-123"}

app = FastAPI(
    title="Banking Connector Service",
    description="Service for connecting to Open Banking providers and fetching data.",
    version="1.0.0"
)

# --- Models ---
class InitiateConnectionRequest(BaseModel):
    provider_id: str
    redirect_uri: HttpUrl

class InitiateConnectionResponse(BaseModel):
    consent_url: HttpUrl
    state: Optional[str] = None

class CallbackResponse(BaseModel):
    connection_id: str
    status: str
    message: str
    task_id: Optional[str] = None

class ProviderInfo(BaseModel):
    id: str
    display_name: str
    configured: str

class Transaction(BaseModel):
    provider_transaction_id: str
    date: datetime.date
    description: str
    amount: float
    currency: str

# --- Endpoints ---
@app.post("/connections/initiate", response_model=InitiateConnectionResponse)
async def initiate_connection(
    request: InitiateConnectionRequest,
    auth_user: dict = Depends(fake_auth_check)
):
    print(f"User {auth_user['user_id']} is initiating connection with {request.provider_id}")
    try:
        provider = get_provider(request.provider_id)
        result = await provider.initiate(auth_user["user_id"], str(request.redirect_uri))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return InitiateConnectionResponse(consent_url=result.consent_url, state=result.state)

@app.get("/connections/callback", response_model=CallbackResponse)
async def handle_provider_callback(
    provider_id: str = "mock_bank",
    code: Optional[str] = None,
    connection_id: Optional[str] = None,
    state: Optional[str] = None,
    auth_user: dict = Depends(fake_auth_check),
):
    try:
        provider = get_provider(provider_id)
        callback_result = await provider.handle_callback(
            user_id=auth_user["user_id"],
            code=code,
            connection_id=connection_id,
            state=state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    save_connection_metadata(callback_result.connection_id, callback_result.metadata)

    task_id = None
    if callback_result.transactions:
        task = import_transactions_task.delay(callback_result.connection_id, callback_result.transactions)
        task_id = task.id

    return CallbackResponse(
        connection_id=callback_result.connection_id,
        status=callback_result.status,
        message=callback_result.message,
        task_id=task_id,
    )


@app.get("/providers", response_model=List[ProviderInfo])
async def list_available_providers():
    return [ProviderInfo(**provider) for provider in list_providers()]

@app.get("/accounts/{account_id}/transactions", response_model=List[Transaction], deprecated=True)
async def get_transactions(account_id: uuid.UUID):
    return [
        Transaction(provider_transaction_id="txn_1", date=datetime.date(2023, 10, 1), description="Coffee Shop", amount=-3.50, currency="GBP"),
    ]
