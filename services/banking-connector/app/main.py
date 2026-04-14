import datetime
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import hvac
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl

# --- Config ---
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")

# TrueLayer credentials (sandbox by default)
TRUELAYER_CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID", "")
TRUELAYER_CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET", "")
TRUELAYER_REDIRECT_URI = os.getenv("TRUELAYER_REDIRECT_URI", "http://localhost:3000/connect-bank/callback")
# Use sandbox unless TRUELAYER_PRODUCTION=1
_TL_PRODUCTION = os.getenv("TRUELAYER_PRODUCTION", "0") == "1"
TRUELAYER_AUTH_BASE = "https://auth.truelayer.com" if _TL_PRODUCTION else "https://auth.truelayer-sandbox.com"
TRUELAYER_API_BASE = "https://api.truelayer.com" if _TL_PRODUCTION else "https://api.truelayer-sandbox.com"

TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service:80")

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
from libs.shared_auth.plan_limits import PlanLimits, get_plan_limits

from .connection_store import get_connection_count, increment_connection_count

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Banking Connector Service",
    description="Service for connecting to Open Banking providers and fetching data.",
    version="1.0.0"
)

# --- Models ---
class InitiateConnectionRequest(BaseModel):
    provider_id: str = "truelayer"
    redirect_uri: Optional[str] = None

class InitiateConnectionResponse(BaseModel):
    consent_url: str
    provider: str

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


ALLOWED_REDIRECT_DOMAINS = {"localhost", "127.0.0.1"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- Endpoints ---
@app.post("/connections/initiate", response_model=InitiateConnectionResponse)
async def initiate_connection(
    request: InitiateConnectionRequest,
    user_id: str = Depends(get_current_user_id),
    limits: PlanLimits = Depends(get_plan_limits),
):
    current = get_connection_count(user_id)
    if current >= limits.bank_connections_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Bank connection limit for your plan ({limits.plan}) is "
                f"{limits.bank_connections_limit}. Disconnect an existing connection or upgrade."
            ),
        )
    logger.info("User %s initiating %s connection", user_id, request.provider_id)
    redirect_uri = request.redirect_uri or TRUELAYER_REDIRECT_URI

    if TRUELAYER_CLIENT_ID:
        # Real TrueLayer OAuth URL
        scope = "info accounts balance cards transactions direct_debits standing_orders offline_access"
        params = (
            f"response_type=code"
            f"&client_id={TRUELAYER_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope.replace(' ', '%20')}"
            f"&providers=uk-ob-all%20uk-oauth-all"
            f"&state={user_id}"
        )
        consent_url = f"{TRUELAYER_AUTH_BASE}/?{params}"
        provider = "truelayer" + ("" if _TL_PRODUCTION else "-sandbox")
    else:
        # Developer mode: use TrueLayer sandbox demo URL (no credentials needed)
        consent_url = (
            f"{TRUELAYER_AUTH_BASE}/?response_type=code"
            f"&client_id=selfmonitor-dev"
            f"&redirect_uri={redirect_uri}"
            f"&scope=info%20accounts%20balance%20transactions%20offline_access"
            f"&providers=uk-ob-all%20uk-oauth-all"
            f"&state={user_id}"
        )
        provider = "truelayer-sandbox-demo"

    return InitiateConnectionResponse(consent_url=consent_url, provider=provider)

@app.get("/connections/callback", response_model=CallbackResponse)
async def handle_provider_callback(
    code: str,
    state: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    current = get_connection_count(user_id)
    if current >= limits.bank_connections_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Bank connection limit for your plan ({limits.plan}) is "
                f"{limits.bank_connections_limit}. Cannot add another connection."
            ),
        )

    connection_id = uuid.uuid4()
    access_token: str
    refresh_token: str
    transactions: List[Transaction]

    if TRUELAYER_CLIENT_ID and TRUELAYER_CLIENT_SECRET:
        # Real TrueLayer token exchange
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                token_resp = await client.post(
                    f"{TRUELAYER_AUTH_BASE}/connect/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": TRUELAYER_CLIENT_ID,
                        "client_secret": TRUELAYER_CLIENT_SECRET,
                        "redirect_uri": TRUELAYER_REDIRECT_URI,
                        "code": code,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_resp.raise_for_status()
                token_data = token_resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"TrueLayer token exchange failed: {e}") from e

        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        save_tokens_to_vault(str(connection_id), access_token, refresh_token)

        # Fetch real transactions from TrueLayer
        transactions = await _fetch_truelayer_transactions(access_token)
    else:
        # Sandbox demo: use mock data
        logger.info("TrueLayer credentials not configured — using sandbox demo data")
        access_token = f"acc-tok-{uuid.uuid4()}"
        refresh_token = f"ref-tok-{uuid.uuid4()}"
        save_tokens_to_vault(str(connection_id), access_token, refresh_token)
        transactions = _sandbox_demo_transactions()

    # Dispatch to Celery if available, otherwise skip (dev mode)
    task_id = "dev-no-celery"
    if _celery_available and import_transactions_task is not None:
        task = import_transactions_task.delay(
            str(connection_id),
            user_id,
            bearer_token,
            [t.model_dump() for t in transactions],
        )
        task_id = task.id

    increment_connection_count(user_id)

    return CallbackResponse(
        connection_id=connection_id,
        status="processing",
        message=f"Connected. {len(transactions)} transactions queued for import.",
        task_id=task_id,
    )


async def _fetch_truelayer_transactions(access_token: str) -> List[Transaction]:
    """Fetch transactions from all TrueLayer accounts."""
    txns: List[Transaction] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            accts_resp = await client.get(f"{TRUELAYER_API_BASE}/data/v1/accounts", headers=headers)
            if not accts_resp.is_success:
                return _sandbox_demo_transactions()
            accounts = accts_resp.json().get("results", [])
            for acct in accounts[:5]:  # cap at 5 accounts
                acct_id = acct.get("account_id", "")
                if not acct_id:
                    continue
                tx_resp = await client.get(
                    f"{TRUELAYER_API_BASE}/data/v1/accounts/{acct_id}/transactions",
                    headers=headers,
                    params={"from": (datetime.date.today() - datetime.timedelta(days=90)).isoformat()},
                )
                if tx_resp.is_success:
                    for raw in tx_resp.json().get("results", []):
                        try:
                            txns.append(Transaction(
                                provider_transaction_id=raw.get("transaction_id", str(uuid.uuid4())),
                                date=datetime.date.fromisoformat(raw.get("timestamp", "")[:10]),
                                description=raw.get("description", ""),
                                amount=float(raw.get("amount", 0)),
                                currency=raw.get("currency", "GBP"),
                            ))
                        except Exception:
                            pass
    except Exception as e:
        logger.warning("TrueLayer transaction fetch failed: %s", e)
    return txns or _sandbox_demo_transactions()


def _sandbox_demo_transactions() -> List[Transaction]:
    """UK-realistic demo transactions for sandbox/dev mode."""
    today = datetime.date.today()
    return [
        Transaction(provider_transaction_id="tl-1", date=today, description="Tesco Superstore", amount=-67.40, currency="GBP"),
        Transaction(provider_transaction_id="tl-2", date=today - datetime.timedelta(days=1), description="Client Payment — Invoice #42", amount=1200.00, currency="GBP"),
        Transaction(provider_transaction_id="tl-3", date=today - datetime.timedelta(days=2), description="AWS", amount=-45.32, currency="GBP"),
        Transaction(provider_transaction_id="tl-4", date=today - datetime.timedelta(days=3), description="TfL — Monthly Travel Card", amount=-194.00, currency="GBP"),
        Transaction(provider_transaction_id="tl-5", date=today - datetime.timedelta(days=5), description="Freelance Project Payment", amount=850.00, currency="GBP"),
        Transaction(provider_transaction_id="tl-6", date=today - datetime.timedelta(days=7), description="Adobe Creative Cloud", amount=-54.99, currency="GBP"),
        Transaction(provider_transaction_id="tl-7", date=today - datetime.timedelta(days=8), description="Virgin Media Broadband", amount=-42.00, currency="GBP"),
        Transaction(provider_transaction_id="tl-8", date=today - datetime.timedelta(days=10), description="Co-Working Space — Monthly", amount=-280.00, currency="GBP"),
        Transaction(provider_transaction_id="tl-9", date=today - datetime.timedelta(days=12), description="HMRC Corporation Tax", amount=-1250.00, currency="GBP"),
        Transaction(provider_transaction_id="tl-10", date=today - datetime.timedelta(days=14), description="Client Payment — Invoice #39", amount=2400.00, currency="GBP"),
    ]


@app.post("/connections/{connection_id}/sync", response_model=CallbackResponse)
async def sync_connection(
    connection_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    """
    Manual re-sync: pull latest transactions for an existing connection.
    Only triggered by explicit user action (button press) — never automatic.
    """
    # Retrieve tokens from Vault
    access_token: Optional[str] = None
    if vault_available and vault_client:
        try:
            secret = vault_client.secrets.kv.v2.read_secret_version(
                path=f"kv/banking-connections/{connection_id}"
            )
            access_token = secret["data"]["data"].get("access_token")
        except Exception:
            pass

    if access_token and TRUELAYER_CLIENT_ID:
        transactions = await _fetch_truelayer_transactions(access_token)
    else:
        transactions = _sandbox_demo_transactions()

    task_id = "dev-no-celery"
    if _celery_available and import_transactions_task is not None:
        task = import_transactions_task.delay(
            str(connection_id), user_id, bearer_token,
            [t.model_dump() for t in transactions],
        )
        task_id = task.id

    return CallbackResponse(
        connection_id=connection_id,
        status="syncing",
        message=f"Sync started. {len(transactions)} transactions queued.",
        task_id=task_id,
    )

@app.get("/accounts/{account_id}/transactions", response_model=List[Transaction], deprecated=True)
async def get_transactions(account_id: uuid.UUID):
    return [
        Transaction(provider_transaction_id="txn_1", date=datetime.date(2023, 10, 1), description="Coffee Shop", amount=-3.50, currency="GBP"),
    ]
