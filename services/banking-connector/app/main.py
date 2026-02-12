from fastapi import Depends, FastAPI, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uuid
import datetime
import os
import hvac
from .celery_app import import_transactions_task

# --- Vault Client Setup ---
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"

vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
try:
    if vault_client.is_authenticated():
        print("Successfully authenticated with Vault.")
    else:
        print("Error: Could not authenticate with Vault.")
except Exception as exc:
    print(f"Warning: Vault authentication check failed during startup: {exc}")


def save_tokens_to_vault(connection_id: str, access_token: str, refresh_token: str):
    """Saves sensitive tokens to Vault."""
    secret_path = f"kv/banking-connections/{connection_id}"
    try:
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=secret_path,
            secret=dict(access_token=access_token, refresh_token=refresh_token),
        )
        print(f"Tokens for connection {connection_id} securely stored in Vault.")
    except Exception as e:
        print(f"Error storing tokens in Vault: {e}")


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

class CallbackResponse(BaseModel):
    connection_id: uuid.UUID
    status: str
    message: str
    task_id: str

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
    user_id: str = Depends(get_current_user_id)
):
    print(f"User {user_id} is initiating connection with {request.provider_id}")
    consent_url = f"https://fake-bank-provider.com/consent?client_id={request.provider_id}&redirect_uri={request.redirect_uri}&scope=transactions"
    return InitiateConnectionResponse(consent_url=consent_url)

@app.get("/connections/callback", response_model=CallbackResponse)
async def handle_provider_callback(
    code: str,
    state: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    print(f"Exchanging code '{code}' for an access token. State: {state}")
    connection_id = uuid.uuid4()

    # 1. Simulate receiving sensitive tokens from the bank
    mock_access_token = f"acc-tok-{uuid.uuid4()}"
    mock_refresh_token = f"ref-tok-{uuid.uuid4()}"

    # 2. Securely store these tokens in Vault instead of our own database
    save_tokens_to_vault(str(connection_id), mock_access_token, mock_refresh_token)

    # 3. Simulate fetching transactions after successful connection
    mock_transactions = [
        Transaction(provider_transaction_id="provider-txn-1", date=datetime.date.today(), description="Tesco", amount=-25.50, currency="GBP"),
        Transaction(provider_transaction_id="provider-txn-2", date=datetime.date.today() - datetime.timedelta(days=1), description="Amazon", amount=-12.99, currency="GBP"),
    ]

    # Dispatch the task to the Celery queue.
    # We convert Pydantic models to dicts as Celery works best with simple data types.
    task = import_transactions_task.delay(
        str(connection_id),
        user_id,
        bearer_token,
        [t.dict() for t in mock_transactions],
    )

    return CallbackResponse(
        connection_id=connection_id,
        status="processing",
        message="Connection established. Transaction import has been dispatched to a background worker.",
        task_id=task.id
    )

@app.get("/accounts/{account_id}/transactions", response_model=List[Transaction], deprecated=True)
async def get_transactions(account_id: uuid.UUID):
    return [
        Transaction(provider_transaction_id="txn_1", date=datetime.date(2023, 10, 1), description="Coffee Shop", amount=-3.50, currency="GBP"),
    ]
