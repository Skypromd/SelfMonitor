import csv
import datetime
import io
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import hvac
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

# --- Config ---
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")

# Try to import Celery task — gracefully degrade if broker unavailable
try:
    from .celery_app import import_transactions_task
    _celery_available = True
except Exception:
    import_transactions_task = None  # type: ignore[assignment]
    _celery_available = False

logger = logging.getLogger(__name__)

vault_available = False
vault_client = None
try:
    _vc = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if _vc.is_authenticated():
        vault_client = _vc
        vault_available = True
        print("Successfully authenticated with Vault.")
    else:
        print("Warning: Could not authenticate with Vault.")
except Exception as exc:
    print(f"Warning: Vault unavailable - tokens will not be persisted: {exc}")


def save_tokens_to_vault(connection_id: str, access_token: str, refresh_token: str):
    """Saves sensitive tokens to Vault."""
    if not vault_available or not vault_client:
        logger.warning("Skipping token persistence because Vault is unavailable.")
        return

    secret_path = f"kv/banking-connections/{connection_id}"
    try:
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=secret_path,
            secret=dict(access_token=access_token, refresh_token=refresh_token),
        )
        logger.info("Tokens stored in Vault for connection %s", connection_id)
    except Exception as e:
        logger.error("Error storing tokens in Vault: %s", e)


for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

_AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret")
_AUTH_ALGORITHM = "HS256"


def _get_jwt_claims(token: str = Depends(get_bearer_token)) -> dict:
    """Decode JWT and return full claims dict (non-raising — returns {} on error)."""
    try:
        from jose import jwt as _jwt  # noqa: PLC0415
        return _jwt.decode(token, _AUTH_SECRET_KEY, algorithms=[_AUTH_ALGORITHM])
    except Exception:
        return {}

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


# --- Provider catalogue ---
_PROVIDERS: List[Dict[str, str]] = [
    {"id": "saltedge", "display_name": "Salt Edge", "configured": "true", "logo_url": "https://cdn.mynettax.app/providers/saltedge.png"},
    {"id": "truelayer", "display_name": "TrueLayer", "configured": "true", "logo_url": "https://cdn.mynettax.app/providers/truelayer.png"},
    {"id": "mock_bank", "display_name": "Mock Bank (dev)", "configured": "true", "logo_url": "https://cdn.mynettax.app/providers/mock_bank.png"},
]

_TRUELAYER_CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID", "truelayer-client-id")
_TRUELAYER_AUTH_URL = os.getenv("TRUELAYER_AUTH_URL", "https://auth.truelayer.com")

_TRANSACTIONS_INTERNAL_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:8000")


@app.get("/providers")
async def list_providers():
    return _PROVIDERS


@app.get("/connections/sync-quota")
async def get_sync_quota(
    user_id: str = Depends(get_current_user_id),
    claims: dict = Depends(_get_jwt_claims),
):
    from .bank_sync_quota import sync_used_today  # noqa: PLC0415
    daily_limit = int(claims.get("bank_sync_daily_limit", 3))
    used = sync_used_today(user_id)
    remaining = max(0, daily_limit - used)
    return {
        "daily_limit": daily_limit,
        "used_today": used,
        "remaining": remaining,
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- Endpoints ---
class InitiateConnectionResponse(BaseModel):
    consent_url: str
    provider: str


@app.post("/connections/initiate")
async def initiate_connection(
    request: InitiateConnectionRequest,
    user_id: str = Depends(get_current_user_id)
):
    print(f"User {user_id} is initiating connection with {request.provider_id}")
    pid = request.provider_id
    redirect = str(request.redirect_uri)
    if pid == "truelayer":
        consent_url = (
            f"{_TRUELAYER_AUTH_URL}/?response_type=code&client_id={_TRUELAYER_CLIENT_ID}"
            f"&redirect_uri={redirect}&scope=accounts%20transactions%20offline_access"
        )
    else:
        consent_url = (
            f"https://fake-bank-provider.com/consent?client_id={pid}"
            f"&redirect_uri={redirect}&scope=transactions"
        )
    return {"consent_url": consent_url, "provider": pid}

@app.get("/connections/callback", response_model=CallbackResponse)
async def handle_provider_callback(
    code: str,
    state: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    logger.info("Exchanging authorization code for access token")
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

    # Dispatch to Celery if available, otherwise skip (dev mode)
    task_id = "dev-no-celery"
    if _celery_available and import_transactions_task is not None:
        task = import_transactions_task.delay(
            str(connection_id),
            user_id,
            bearer_token,
            [t.model_dump() for t in mock_transactions],
        )
        task_id = task.id

    return CallbackResponse(
        connection_id=connection_id,
        status="processing",
        message="Connection established. Transaction import has been dispatched to a background worker.",
        task_id=task_id
    )

@app.get("/accounts/{account_id}/transactions", response_model=List[Transaction], deprecated=True)
async def get_transactions(account_id: uuid.UUID):
    return [
        Transaction(provider_transaction_id="txn_1", date=datetime.date(2023, 10, 1), description="Coffee Shop", amount=-3.50, currency="GBP"),
    ]


def _escape_csv_field(value: str) -> str:
    """Wrap field in quotes and double any internal quotes."""
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


@app.get("/exports/statement-csv")
async def export_statement_csv(
    days: int = 365,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{_TRANSACTIONS_INTERNAL_URL}/transactions/me",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=exc.response.json().get("detail", str(exc)),
            ) from exc

    raw: List[Dict[str, Any]] = resp.json()
    rows = [t for t in raw if t.get("date", "") >= cutoff]

    output = io.StringIO()
    headers = ["id", "date", "description", "amount", "currency", "category"]
    output.write(",".join(headers) + "\n")
    for row in rows:
        line = ",".join([
            _escape_csv_field(str(row.get("id", ""))),
            _escape_csv_field(str(row.get("date", ""))),
            _escape_csv_field(str(row.get("description", ""))),
            _escape_csv_field(str(row.get("amount", ""))),
            _escape_csv_field(str(row.get("currency", ""))),
            _escape_csv_field(str(row.get("category") or "")),
        ])
        output.write(line + "\n")

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
