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
from pydantic import BaseModel

# --- Config ---
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")

BANKING_OPEN_BANKING_PROVIDER = os.getenv("BANKING_OPEN_BANKING_PROVIDER", "saltedge").strip().lower()
OAUTH_REDIRECT_URI_DEFAULT = os.getenv(
    "BANKING_OAUTH_REDIRECT_URI",
    os.getenv("TRUELAYER_REDIRECT_URI", "http://localhost:3000/connect-bank/callback"),
)

# TrueLayer credentials (optional secondary / demo path)
TRUELAYER_CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID", "")
TRUELAYER_CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET", "")
TRUELAYER_REDIRECT_URI = os.getenv("TRUELAYER_REDIRECT_URI", OAUTH_REDIRECT_URI_DEFAULT)
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


def save_tokens_to_vault(
    connection_id: str,
    access_token: str,
    refresh_token: str,
    *,
    provider: str = "truelayer",
    saltedge_connection_id: Optional[str] = None,
) -> None:
    if not vault_available or not vault_client:
        logger.warning("Skipping token persistence because Vault is unavailable.")
        return

    secret_path = f"kv/banking-connections/{connection_id}"
    payload: Dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "provider": provider,
    }
    if saltedge_connection_id is not None:
        payload["saltedge_connection_id"] = saltedge_connection_id
    try:
        vault_client.secrets.kv.v2.create_or_update_secret(path=secret_path, secret=payload)
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
from libs.shared_auth.plan_enforcement_log import log_plan_enforcement_denial
from libs.shared_auth.plan_limits import PlanLimits, get_plan_limits
from libs.shared_http.request_id import get_request_id

from .bank_sync_quota import consume_sync_slot_or_raise, sync_status
from .connection_store import get_connection_count, increment_connection_count
from .providers.registry import get_provider
from .providers.saltedge import SaltedgeProvider

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Banking Connector Service",
    description="Service for connecting to Open Banking providers and fetching data.",
    version="1.0.0"
)

# --- Models ---
class InitiateConnectionRequest(BaseModel):
    provider_id: Optional[str] = None
    redirect_uri: Optional[str] = None

class InitiateConnectionResponse(BaseModel):
    consent_url: str
    provider: str

class CallbackResponse(BaseModel):
    connection_id: str
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
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    current = get_connection_count(user_id)
    if current >= limits.bank_connections_limit:
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="bank_connections",
            reason="connection_cap_exceeded",
            current=current,
            limit_value=limits.bank_connections_limit,
            request_id=get_request_id(),
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Bank connection limit for your plan ({limits.plan}) is "
                f"{limits.bank_connections_limit}. Disconnect an existing connection or upgrade."
            ),
        )
    provider_key = (request.provider_id or BANKING_OPEN_BANKING_PROVIDER or "saltedge").strip().lower()
    redirect_uri = str(request.redirect_uri or OAUTH_REDIRECT_URI_DEFAULT)
    logger.info("User %s initiating %s connection", user_id, provider_key)

    if provider_key == "mock_bank":
        mock = get_provider("mock_bank")
        init = await mock.initiate(user_id, redirect_uri)
        return InitiateConnectionResponse(consent_url=init.consent_url, provider="mock_bank")

    if provider_key == "saltedge":
        se = SaltedgeProvider()
        if se.is_configured():
            init = await se.initiate(user_id, redirect_uri)
            return InitiateConnectionResponse(consent_url=init.consent_url, provider="saltedge")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Salt Edge Open Banking is not configured (set SALTEDGE_APP_ID and SALTEDGE_SECRET). "
                'For a local demo without Salt Edge, call initiate with provider_id "truelayer".'
            ),
        )

    if provider_key != "truelayer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider_id: {provider_key}. Use saltedge, truelayer, or mock_bank.",
        )

    if TRUELAYER_CLIENT_ID:
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

def _transactions_from_provider_rows(rows: List[Dict[str, Any]]) -> List[Transaction]:
    out: List[Transaction] = []
    for raw in rows:
        try:
            pid = raw.get("provider_transaction_id")
            if pid is None:
                continue
            dval = raw.get("date")
            if isinstance(dval, str):
                d = datetime.date.fromisoformat(dval[:10])
            elif isinstance(dval, datetime.date):
                d = dval
            else:
                d = datetime.date.today()
            out.append(
                Transaction(
                    provider_transaction_id=str(pid),
                    date=d,
                    description=str(raw.get("description", "")),
                    amount=float(raw.get("amount", 0)),
                    currency=str(raw.get("currency", "GBP")),
                )
            )
        except (TypeError, ValueError):
            continue
    return out


async def _complete_connection(
    user_id: str,
    bearer_token: str,
    transactions: List[Transaction],
    *,
    internal_connection_id: uuid.UUID,
    access_token: str,
    refresh_token: str,
    provider: str,
    saltedge_connection_id: Optional[str] = None,
) -> CallbackResponse:
    save_tokens_to_vault(
        str(internal_connection_id),
        access_token,
        refresh_token,
        provider=provider,
        saltedge_connection_id=saltedge_connection_id,
    )
    task_id = "dev-no-celery"
    if _celery_available and import_transactions_task is not None:
        task = import_transactions_task.delay(
            str(internal_connection_id),
            user_id,
            bearer_token,
            [t.model_dump() for t in transactions],
        )
        task_id = task.id
    increment_connection_count(user_id)
    return CallbackResponse(
        connection_id=str(internal_connection_id),
        status="processing",
        message=f"Connected. {len(transactions)} transactions queued for import.",
        task_id=task_id,
    )


@app.get("/connections/callback", response_model=CallbackResponse)
async def handle_provider_callback(
    code: Optional[str] = None,
    connection_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    state: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    current = get_connection_count(user_id)
    if current >= limits.bank_connections_limit:
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="bank_connections",
            reason="connection_cap_exceeded",
            current=current,
            limit_value=limits.bank_connections_limit,
            request_id=get_request_id(),
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Bank connection limit for your plan ({limits.plan}) is "
                f"{limits.bank_connections_limit}. Cannot add another connection."
            ),
        )

    prov = (provider_id or "").strip().lower()

    if prov == "mock_bank" and code:
        mock = get_provider("mock_bank")
        try:
            result = await mock.handle_callback(user_id, code=code, state=state)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        internal_id = uuid.UUID(result.connection_id)
        transactions = _transactions_from_provider_rows(result.transactions)
        meta = result.metadata or {}
        return await _complete_connection(
            user_id,
            bearer_token,
            transactions,
            internal_connection_id=internal_id,
            access_token=str(meta.get("access_token", "")),
            refresh_token=str(meta.get("refresh_token", "")),
            provider="mock_bank",
        )

    if connection_id and not code:
        se = SaltedgeProvider()
        if not se.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Salt Edge is not configured.",
            )
        try:
            result = await se.handle_callback(user_id, connection_id=connection_id, state=state)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        internal_id = uuid.uuid4()
        transactions = _transactions_from_provider_rows(result.transactions)
        return await _complete_connection(
            user_id,
            bearer_token,
            transactions or _sandbox_demo_transactions(),
            internal_connection_id=internal_id,
            access_token="-",
            refresh_token="-",
            provider="saltedge",
            saltedge_connection_id=str(result.connection_id),
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Missing callback parameters: need code (TrueLayer/mock) or connection_id (Salt Edge).",
        )

    internal_id = uuid.uuid4()
    if TRUELAYER_CLIENT_ID and TRUELAYER_CLIENT_SECRET:
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
        transactions = await _fetch_truelayer_transactions(str(access_token))
        return await _complete_connection(
            user_id,
            bearer_token,
            transactions,
            internal_connection_id=internal_id,
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            provider="truelayer",
        )

    logger.info("TrueLayer credentials not configured — using sandbox demo data")
    access_token = f"acc-tok-{uuid.uuid4()}"
    refresh_token = f"ref-tok-{uuid.uuid4()}"
    transactions = _sandbox_demo_transactions()
    return await _complete_connection(
        user_id,
        bearer_token,
        transactions,
        internal_connection_id=internal_id,
        access_token=access_token,
        refresh_token=refresh_token,
        provider="truelayer",
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


@app.get("/connections/sync-quota")
async def get_sync_quota(
    user_id: str = Depends(get_current_user_id),
    limits: PlanLimits = Depends(get_plan_limits),
):
    return sync_status(user_id, limits.bank_sync_daily_limit)


@app.post("/connections/{connection_id}/sync", response_model=CallbackResponse)
async def sync_connection(
    connection_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
):
    """
    Manual re-sync: pull latest transactions for an existing connection.
    Only triggered by explicit user action (button press) — never automatic.
    """
    access_token: Optional[str] = None
    provider = "truelayer"
    saltedge_cid: Optional[str] = None
    if vault_available and vault_client:
        try:
            secret = vault_client.secrets.kv.v2.read_secret_version(
                path=f"kv/banking-connections/{connection_id}"
            )
            blob = secret["data"]["data"]
            access_token = blob.get("access_token")
            provider = str(blob.get("provider") or "truelayer")
            saltedge_cid = blob.get("saltedge_connection_id")
            if saltedge_cid is not None:
                saltedge_cid = str(saltedge_cid)
        except Exception:
            pass

    if provider == "saltedge" and saltedge_cid:
        se = SaltedgeProvider()
        if se.is_configured():
            raw = await se.fetch_transactions(saltedge_cid)
            transactions = _transactions_from_provider_rows(raw) or _sandbox_demo_transactions()
        else:
            transactions = _sandbox_demo_transactions()
    elif (
        provider == "truelayer"
        and access_token
        and not str(access_token).startswith("acc-tok-")
        and TRUELAYER_CLIENT_ID
    ):
        transactions = await _fetch_truelayer_transactions(str(access_token))
    else:
        transactions = _sandbox_demo_transactions()

    consume_sync_slot_or_raise(
        user_id,
        limits.bank_sync_daily_limit,
        plan=limits.plan,
        compliance_bearer_token=bearer_token,
    )

    task_id = "dev-no-celery"
    if _celery_available and import_transactions_task is not None:
        task = import_transactions_task.delay(
            str(connection_id), user_id, bearer_token,
            [t.model_dump() for t in transactions],
        )
        task_id = task.id

    return CallbackResponse(
        connection_id=str(connection_id),
        status="syncing",
        message=f"Sync started. {len(transactions)} transactions queued.",
        task_id=task_id,
    )

@app.get("/accounts/{account_id}/transactions", response_model=List[Transaction], deprecated=True)
async def get_transactions(account_id: uuid.UUID):
    return [
        Transaction(provider_transaction_id="txn_1", date=datetime.date(2023, 10, 1), description="Coffee Shop", amount=-3.50, currency="GBP"),
    ]
