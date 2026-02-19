from collections import defaultdict, deque
from datetime import timedelta
from typing import Annotated, Any, Dict, Optional
import datetime
import hashlib
import hmac
import io
import json
import os
import secrets
import threading
import time
import uuid

import httpx
from fastapi import FastAPI, Depends, HTTPException, status, Response, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, ValidationError
import pyotp
import qrcode
from prometheus_fastapi_instrumentator import Instrumentator

# --- Configuration ---
# The secret key is now read from an environment variable for better security.
# A default value is provided for convenience in local development without Docker.


def _parse_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _parse_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_non_negative_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = _parse_positive_int_env("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
REFRESH_TOKEN_EXPIRE_DAYS = _parse_positive_int_env("AUTH_REFRESH_TOKEN_EXPIRE_DAYS", 30)
PASSWORD_MIN_LENGTH = _parse_positive_int_env("AUTH_PASSWORD_MIN_LENGTH", 12)
MAX_FAILED_LOGIN_ATTEMPTS = _parse_positive_int_env("AUTH_MAX_FAILED_LOGIN_ATTEMPTS", 5)
ACCOUNT_LOCKOUT_MINUTES = _parse_positive_int_env("AUTH_ACCOUNT_LOCKOUT_MINUTES", 15)
LOGIN_IP_WINDOW_SECONDS = _parse_positive_int_env("AUTH_LOGIN_IP_WINDOW_SECONDS", 60)
LOGIN_IP_MAX_ATTEMPTS = _parse_positive_int_env("AUTH_LOGIN_IP_MAX_ATTEMPTS", 30)
EMAIL_VERIFICATION_CODE_TTL_MINUTES = _parse_positive_int_env(
    "AUTH_EMAIL_VERIFICATION_CODE_TTL_MINUTES",
    15,
)
EMAIL_VERIFICATION_MAX_ATTEMPTS = _parse_positive_int_env("AUTH_EMAIL_VERIFICATION_MAX_ATTEMPTS", 5)
REQUIRE_VERIFIED_EMAIL_FOR_LOGIN = _parse_bool_env("AUTH_REQUIRE_VERIFIED_EMAIL_FOR_LOGIN", False)
EMAIL_VERIFICATION_DEBUG_RETURN_CODE = _parse_bool_env("AUTH_EMAIL_VERIFICATION_DEBUG_RETURN_CODE", False)
TOTP_VALID_WINDOW_STEPS = _parse_positive_int_env("AUTH_TOTP_VALID_WINDOW_STEPS", 1)
STEP_UP_MAX_AGE_MINUTES = _parse_positive_int_env("AUTH_STEP_UP_MAX_AGE_MINUTES", 10)
REQUIRE_ADMIN_2FA = _parse_bool_env("AUTH_REQUIRE_ADMIN_2FA", True)
AUTH_EMERGENCY_LOCKDOWN_DEFAULT_MINUTES = _parse_positive_int_env(
    "AUTH_EMERGENCY_LOCKDOWN_DEFAULT_MINUTES",
    30,
)
AUTH_EMERGENCY_LOCKDOWN_MAX_MINUTES = _parse_positive_int_env(
    "AUTH_EMERGENCY_LOCKDOWN_MAX_MINUTES",
    1440,
)
AUTH_SECURITY_ALERTS_ENABLED = _parse_bool_env("AUTH_SECURITY_ALERTS_ENABLED", False)
AUTH_SECURITY_ALERT_EMAIL_ENABLED = _parse_bool_env("AUTH_SECURITY_ALERT_EMAIL_ENABLED", False)
AUTH_SECURITY_ALERT_PUSH_ENABLED = _parse_bool_env("AUTH_SECURITY_ALERT_PUSH_ENABLED", False)
AUTH_SECURITY_ALERT_EMAIL_PROVIDER = os.getenv("AUTH_SECURITY_ALERT_EMAIL_PROVIDER", "webhook").strip().lower()
AUTH_SECURITY_ALERT_PUSH_PROVIDER = os.getenv("AUTH_SECURITY_ALERT_PUSH_PROVIDER", "webhook").strip().lower()
AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL = os.getenv("AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL", "").strip()
AUTH_SECURITY_ALERT_PUSH_DISPATCH_URL = os.getenv("AUTH_SECURITY_ALERT_PUSH_DISPATCH_URL", "").strip()
AUTH_SECURITY_ALERT_EMAIL_FROM = os.getenv("AUTH_SECURITY_ALERT_EMAIL_FROM", "security@selfmonitor.app").strip()
AUTH_SECURITY_ALERT_PUSH_TITLE_PREFIX = os.getenv(
    "AUTH_SECURITY_ALERT_PUSH_TITLE_PREFIX",
    "SelfMonitor Security",
).strip()
AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET = os.getenv("AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET", "").strip()
AUTH_SECURITY_ALERT_WEBHOOK_SIGNATURE_TTL_SECONDS = _parse_positive_int_env(
    "AUTH_SECURITY_ALERT_WEBHOOK_SIGNATURE_TTL_SECONDS",
    300,
)
AUTH_SECURITY_ALERT_SENDGRID_API_URL = os.getenv(
    "AUTH_SECURITY_ALERT_SENDGRID_API_URL",
    "https://api.sendgrid.com/v3/mail/send",
).strip()
AUTH_SECURITY_ALERT_SENDGRID_API_KEY = os.getenv("AUTH_SECURITY_ALERT_SENDGRID_API_KEY", "").strip()
AUTH_SECURITY_ALERT_EXPO_PUSH_API_URL = os.getenv(
    "AUTH_SECURITY_ALERT_EXPO_PUSH_API_URL",
    "https://exp.host/--/api/v2/push/send",
).strip()
AUTH_SECURITY_ALERT_FCM_API_URL = os.getenv(
    "AUTH_SECURITY_ALERT_FCM_API_URL",
    "https://fcm.googleapis.com/fcm/send",
).strip()
AUTH_SECURITY_ALERT_FCM_SERVER_KEY = os.getenv("AUTH_SECURITY_ALERT_FCM_SERVER_KEY", "").strip()
AUTH_SECURITY_ALERT_COOLDOWN_MINUTES = _parse_positive_int_env("AUTH_SECURITY_ALERT_COOLDOWN_MINUTES", 30)
AUTH_SECURITY_ALERT_DELIVERY_RETRY_ATTEMPTS = _parse_positive_int_env(
    "AUTH_SECURITY_ALERT_DELIVERY_RETRY_ATTEMPTS",
    2,
)
AUTH_SECURITY_ALERT_DELIVERY_RETRY_BASE_DELAY_SECONDS = max(
    _parse_non_negative_float_env("AUTH_SECURITY_ALERT_DELIVERY_RETRY_BASE_DELAY_SECONDS", 0.3),
    0.05,
)
AUTH_SECURITY_ALERT_DISPATCH_TIMEOUT_SECONDS = max(
    _parse_non_negative_float_env("AUTH_SECURITY_ALERT_DISPATCH_TIMEOUT_SECONDS", 5.0),
    0.1,
)
AUTH_SECURITY_ALERT_RECEIPTS_ENABLED = _parse_bool_env("AUTH_SECURITY_ALERT_RECEIPTS_ENABLED", False)
AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET = os.getenv("AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET", "").strip()
AUTH_MOBILE_ATTESTATION_ENABLED = _parse_bool_env("AUTH_MOBILE_ATTESTATION_ENABLED", True)
AUTH_MOBILE_ATTESTATION_TOKEN_TTL_MINUTES = _parse_positive_int_env("AUTH_MOBILE_ATTESTATION_TOKEN_TTL_MINUTES", 10)
AUTH_MOBILE_ATTESTATION_REQUIRE_RECENT_AUTH = _parse_bool_env(
    "AUTH_MOBILE_ATTESTATION_REQUIRE_RECENT_AUTH",
    True,
)
MOBILE_ATTESTATION_HEADER = "x-selfmonitor-mobile-attestation"
MOBILE_INSTALLATION_ID_HEADER = "x-selfmonitor-mobile-installation-id"
AUTH_LEGAL_CURRENT_VERSION = os.getenv("AUTH_LEGAL_CURRENT_VERSION", "2026-Q1").strip() or "2026-Q1"
AUTH_LEGAL_TERMS_URL = os.getenv("AUTH_LEGAL_TERMS_URL", "/terms").strip() or "/terms"
AUTH_LEGAL_EULA_URL = os.getenv("AUTH_LEGAL_EULA_URL", "/eula").strip() or "/eula"
AUTH_REQUIRE_LEGAL_ACCEPTANCE = _parse_bool_env("AUTH_REQUIRE_LEGAL_ACCEPTANCE", False)
AUTH_RUNTIME_STATE_SNAPSHOT_ENABLED = _parse_bool_env("AUTH_RUNTIME_STATE_SNAPSHOT_ENABLED", True)
AUTH_RUNTIME_STATE_SNAPSHOT_PATH = os.getenv(
    "AUTH_RUNTIME_STATE_SNAPSHOT_PATH",
    "/tmp/selfmonitor-auth-runtime-state.json",
).strip()

app = FastAPI(
    title="Auth Service",
    description="Handles user authentication, registration, and token management.",
    version="1.0.0"
)

# --- Observability ---
# This line adds an instrumentator that exposes a /metrics endpoint
Instrumentator().instrument(app).expose(app)

# --- Security Utils ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.UTC)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now, "typ": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.UTC)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "iat": now, "typ": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def build_access_claims(user: "User", token_version: int) -> dict[str, Any]:
    roles = ["user"]
    scopes: list[str] = []
    if user.is_admin:
        roles.append("admin")
        scopes.append("billing:read")
    return {
        "roles": roles,
        "scopes": scopes,
        "is_admin": user.is_admin,
        "tv": token_version,
    }


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _hash_short_code(value: str) -> str:
    digest = hashlib.sha256()
    digest.update(value.encode("utf-8"))
    digest.update(SECRET_KEY.encode("utf-8"))
    return digest.hexdigest()


def _build_login_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _to_utc_datetime(value: Any) -> Optional[datetime.datetime]:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.UTC)
        return value.astimezone(datetime.UTC)
    return None


# --- Models ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    is_two_factor_enabled: bool = False
    email_verified: bool = False
    locked_until: Optional[datetime.datetime] = None
    last_login_at: Optional[datetime.datetime] = None
    legal_accepted_version: Optional[str] = None
    legal_accepted_at: Optional[datetime.datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    refresh_token: str


class TokenData(BaseModel):
    email: Optional[str] = None
    typ: Optional[str] = None
    tv: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class MobileAttestationSessionRequest(BaseModel):
    installation_id: str = Field(min_length=8, max_length=128)


class MobileAttestationSessionResponse(BaseModel):
    token_type: str = "bearer"
    attestation_token: str
    expires_at: datetime.datetime
    installation_id: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class EmailVerificationConfirmRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class EmailVerificationChallengeResponse(BaseModel):
    message: str
    code_sent: bool
    expires_at: datetime.datetime
    debug_code: Optional[str] = None


class EmailVerificationConfirmResponse(BaseModel):
    message: str
    email_verified: bool


class SecurityEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    occurred_at: datetime.datetime
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SecurityEventsResponse(BaseModel):
    total: int
    items: list[SecurityEvent]


class SecurityStateResponse(BaseModel):
    email: EmailStr
    email_verified: bool
    is_two_factor_enabled: bool
    failed_login_attempts: int
    max_failed_login_attempts: int
    locked_until: Optional[datetime.datetime]
    last_login_at: Optional[datetime.datetime]
    password_changed_at: Optional[datetime.datetime]
    legal_current_version: str
    legal_terms_url: str
    legal_eula_url: str
    legal_accepted_version: Optional[str]
    legal_accepted_at: Optional[datetime.datetime]
    has_accepted_current_legal: bool


class SecuritySessionItem(BaseModel):
    session_id: str
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    revoked_at: Optional[datetime.datetime] = None
    revocation_reason: Optional[str] = None


class SecuritySessionsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    items: list[SecuritySessionItem]


class RevokeSessionsResponse(BaseModel):
    message: str
    revoked_sessions: int


class SecurityLockdownRequest(BaseModel):
    lock_minutes: int = Field(default=AUTH_EMERGENCY_LOCKDOWN_DEFAULT_MINUTES, ge=5)


class SecurityLockdownResponse(BaseModel):
    message: str
    locked_until: datetime.datetime
    lock_minutes: int
    revoked_sessions: int


class SecurityPushTokenRegisterRequest(BaseModel):
    push_token: str = Field(min_length=8, max_length=512)
    provider: str = Field(default="expo", pattern="^(expo|fcm)$")


class SecurityPushTokenItem(BaseModel):
    push_token: str
    provider: str
    registered_at: datetime.datetime
    last_used_at: Optional[datetime.datetime] = None
    revoked_at: Optional[datetime.datetime] = None


class SecurityPushTokensResponse(BaseModel):
    total_tokens: int
    items: list[SecurityPushTokenItem]


class SecurityPushTokenRegisterResponse(BaseModel):
    message: str
    total_active_tokens: int


class SecurityPushTokenRevokeResponse(BaseModel):
    message: str
    revoked_tokens: int


class SecurityAlertDeliveryReceiptRequest(BaseModel):
    dispatch_id: str = Field(min_length=8, max_length=128)
    channel: str = Field(pattern="^(email|push)$")
    status: str = Field(pattern="^(delivered|failed|bounced|deferred|opened|clicked)$")
    provider_message_id: Optional[str] = Field(default=None, max_length=256)
    reason: Optional[str] = Field(default=None, max_length=500)
    occurred_at: Optional[datetime.datetime] = None


class SecurityAlertDeliveryReceiptResponse(BaseModel):
    message: str
    dispatch_id: str
    updated: bool


class SecurityAlertDeliveriesResponse(BaseModel):
    total: int
    items: list[Dict[str, Any]]


class LegalPolicyCurrentResponse(BaseModel):
    current_version: str
    terms_url: str
    eula_url: str
    requires_acceptance: bool


class LegalPolicyAcceptRequest(BaseModel):
    version: str = Field(min_length=2, max_length=64)
    source: str = Field(default="web", min_length=2, max_length=64)


class LegalPolicyAcceptResponse(BaseModel):
    message: str
    accepted_version: str
    accepted_at: datetime.datetime
    has_accepted_current_legal: bool


# --- "Database" ---

def _build_user_record(*, email: str, hashed_password: str, is_admin: bool, email_verified: bool) -> Dict[str, Any]:
    now = datetime.datetime.now(datetime.UTC)
    return {
        "user_data": {
            "email": email,
            "is_active": True,
            "is_admin": is_admin,
            "two_factor_secret": None,
            "is_two_factor_enabled": False,
            "email_verified": email_verified,
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": None,
            "token_version": 0,
            "password_changed_at": now,
            "email_verification_code_hash": None,
            "email_verification_expires_at": None,
            "email_verification_attempts": 0,
            "legal_accepted_version": None,
            "legal_accepted_at": None,
        },
        "hashed_password": hashed_password,
    }


fake_users_db: Dict[str, Dict[str, Any]] = {
    "admin@example.com": _build_user_record(
        email="admin@example.com",
        hashed_password=pwd_context.hash("admin_password"),
        is_admin=True,
        email_verified=True,
    )
}
refresh_token_sessions: Dict[str, Dict[str, Any]] = {}
refresh_tokens_by_user: Dict[str, set[str]] = defaultdict(set)
revoked_refresh_tokens: set[str] = set()
security_events_by_user: Dict[str, deque[SecurityEvent]] = defaultdict(lambda: deque(maxlen=200))
login_attempts_by_ip: Dict[str, deque[datetime.datetime]] = defaultdict(deque)
security_alert_cooldowns_by_user: Dict[str, Dict[str, datetime.datetime]] = defaultdict(dict)
security_alert_dispatch_log: Dict[str, deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=100))
security_alert_deliveries_by_id: Dict[str, Dict[str, Any]] = {}
security_push_tokens_by_user: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
runtime_state_snapshot_lock = threading.Lock()


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, SecurityEvent):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, deque)):
        return [_to_json_compatible(item) for item in value]
    return value


def _parse_iso_datetime(value: Any) -> Optional[datetime.datetime]:
    if isinstance(value, datetime.datetime):
        return _to_utc_datetime(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    return _to_utc_datetime(parsed)


def _hydrate_datetime_fields(record: Dict[str, Any], fields: list[str]) -> Dict[str, Any]:
    hydrated = dict(record)
    for field in fields:
        hydrated[field] = _parse_iso_datetime(hydrated.get(field))
    return hydrated


def _persist_runtime_state_snapshot() -> None:
    if not AUTH_RUNTIME_STATE_SNAPSHOT_ENABLED or not AUTH_RUNTIME_STATE_SNAPSHOT_PATH:
        return
    snapshot_path = os.path.abspath(AUTH_RUNTIME_STATE_SNAPSHOT_PATH)
    payload = {
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "fake_users_db": _to_json_compatible(fake_users_db),
        "refresh_token_sessions": _to_json_compatible(refresh_token_sessions),
        "refresh_tokens_by_user": {
            email: sorted(tokens)
            for email, tokens in refresh_tokens_by_user.items()
        },
        "revoked_refresh_tokens": sorted(revoked_refresh_tokens),
        "security_events_by_user": {
            email: [_to_json_compatible(event) for event in events]
            for email, events in security_events_by_user.items()
        },
        "login_attempts_by_ip": {
            ip: [_to_json_compatible(timestamp) for timestamp in attempts]
            for ip, attempts in login_attempts_by_ip.items()
        },
        "security_alert_cooldowns_by_user": _to_json_compatible(security_alert_cooldowns_by_user),
        "security_alert_dispatch_log": {
            email: [_to_json_compatible(item) for item in items]
            for email, items in security_alert_dispatch_log.items()
        },
        "security_alert_deliveries_by_id": _to_json_compatible(security_alert_deliveries_by_id),
        "security_push_tokens_by_user": _to_json_compatible(security_push_tokens_by_user),
    }
    try:
        with runtime_state_snapshot_lock:
            directory = os.path.dirname(snapshot_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(snapshot_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=True)
    except Exception:
        # Snapshot durability is best-effort and must not break auth availability.
        return


def _load_runtime_state_snapshot() -> None:
    if not AUTH_RUNTIME_STATE_SNAPSHOT_ENABLED or not AUTH_RUNTIME_STATE_SNAPSHOT_PATH:
        return
    snapshot_path = os.path.abspath(AUTH_RUNTIME_STATE_SNAPSHOT_PATH)
    if not os.path.exists(snapshot_path):
        return
    try:
        with runtime_state_snapshot_lock:
            with open(snapshot_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
    except Exception:
        return
    if not isinstance(payload, dict):
        return

    users_payload = payload.get("fake_users_db", {})
    if isinstance(users_payload, dict):
        fake_users_db.clear()
        for email, user_record in users_payload.items():
            if not isinstance(user_record, dict):
                continue
            user_data = user_record.get("user_data", {})
            if not isinstance(user_data, dict):
                continue
            hydrated_user_data = _hydrate_datetime_fields(
                user_data,
                [
                    "locked_until",
                    "last_login_at",
                    "password_changed_at",
                    "email_verification_expires_at",
                    "legal_accepted_at",
                ],
            )
            fake_users_db[_normalize_email(str(email))] = {
                "user_data": hydrated_user_data,
                "hashed_password": str(user_record.get("hashed_password", "")),
            }

    refresh_sessions_payload = payload.get("refresh_token_sessions", {})
    if isinstance(refresh_sessions_payload, dict):
        refresh_token_sessions.clear()
        for jti, session in refresh_sessions_payload.items():
            if not isinstance(session, dict):
                continue
            hydrated_session = _hydrate_datetime_fields(
                session,
                ["issued_at", "expires_at", "revoked_at"],
            )
            refresh_token_sessions[str(jti)] = hydrated_session

    refresh_by_user_payload = payload.get("refresh_tokens_by_user", {})
    refresh_tokens_by_user.clear()
    if isinstance(refresh_by_user_payload, dict):
        for email, token_values in refresh_by_user_payload.items():
            if isinstance(token_values, list):
                refresh_tokens_by_user[_normalize_email(str(email))].update(
                    {str(item) for item in token_values if str(item).strip()}
                )

    revoked_payload = payload.get("revoked_refresh_tokens", [])
    revoked_refresh_tokens.clear()
    if isinstance(revoked_payload, list):
        revoked_refresh_tokens.update({str(item) for item in revoked_payload if str(item).strip()})

    events_payload = payload.get("security_events_by_user", {})
    security_events_by_user.clear()
    if isinstance(events_payload, dict):
        for email, events in events_payload.items():
            queue: deque[SecurityEvent] = deque(maxlen=200)
            if isinstance(events, list):
                for event_payload in events:
                    if not isinstance(event_payload, dict):
                        continue
                    try:
                        queue.append(SecurityEvent.model_validate(event_payload))
                    except ValidationError:
                        continue
            security_events_by_user[_normalize_email(str(email))] = queue

    login_attempts_payload = payload.get("login_attempts_by_ip", {})
    login_attempts_by_ip.clear()
    if isinstance(login_attempts_payload, dict):
        for ip, timestamps in login_attempts_payload.items():
            queue: deque[datetime.datetime] = deque()
            if isinstance(timestamps, list):
                for timestamp in timestamps:
                    parsed = _parse_iso_datetime(timestamp)
                    if parsed:
                        queue.append(parsed)
            login_attempts_by_ip[str(ip)] = queue

    cooldowns_payload = payload.get("security_alert_cooldowns_by_user", {})
    security_alert_cooldowns_by_user.clear()
    if isinstance(cooldowns_payload, dict):
        for email, cooldown_map in cooldowns_payload.items():
            if not isinstance(cooldown_map, dict):
                continue
            hydrated_map: Dict[str, datetime.datetime] = {}
            for key, value in cooldown_map.items():
                parsed = _parse_iso_datetime(value)
                if parsed:
                    hydrated_map[str(key)] = parsed
            security_alert_cooldowns_by_user[_normalize_email(str(email))] = hydrated_map

    dispatch_payload = payload.get("security_alert_dispatch_log", {})
    security_alert_dispatch_log.clear()
    if isinstance(dispatch_payload, dict):
        for email, deliveries in dispatch_payload.items():
            queue: deque[Dict[str, Any]] = deque(maxlen=100)
            if isinstance(deliveries, list):
                for item in deliveries:
                    if isinstance(item, dict):
                        queue.append(item)
            security_alert_dispatch_log[_normalize_email(str(email))] = queue

    deliveries_by_id_payload = payload.get("security_alert_deliveries_by_id", {})
    security_alert_deliveries_by_id.clear()
    if isinstance(deliveries_by_id_payload, dict):
        for dispatch_id, item in deliveries_by_id_payload.items():
            if isinstance(item, dict):
                security_alert_deliveries_by_id[str(dispatch_id)] = item

    push_tokens_payload = payload.get("security_push_tokens_by_user", {})
    security_push_tokens_by_user.clear()
    if isinstance(push_tokens_payload, dict):
        for email, token_map in push_tokens_payload.items():
            if not isinstance(token_map, dict):
                continue
            hydrated_token_map: Dict[str, Dict[str, Any]] = {}
            for token_value, token_record in token_map.items():
                if not isinstance(token_record, dict):
                    continue
                hydrated_token_map[str(token_value)] = _hydrate_datetime_fields(
                    token_record,
                    ["registered_at", "last_used_at", "revoked_at"],
                )
            security_push_tokens_by_user[_normalize_email(str(email))] = hydrated_token_map

    if "admin@example.com" not in fake_users_db:
        fake_users_db["admin@example.com"] = _build_user_record(
            email="admin@example.com",
            hashed_password=get_password_hash("admin_password"),
            is_admin=True,
            email_verified=True,
        )


_load_runtime_state_snapshot()


def get_user_record(email: str) -> Optional[Dict[str, Any]]:
    return fake_users_db.get(_normalize_email(email))


def get_user(email: str) -> Optional[User]:
    user_record = get_user_record(email)
    if not user_record:
        return None
    return User(**user_record["user_data"])


def _truncate_text(value: str, limit: int = 280) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: max(limit - 3, 0)]}..."


def _normalize_push_provider(value: str) -> str:
    candidate = value.strip().lower()
    return candidate if candidate in {"expo", "fcm"} else "expo"


def _build_webhook_signature_headers(payload: Dict[str, Any], secret: str) -> Dict[str, str]:
    if not secret:
        return {}
    timestamp = str(int(datetime.datetime.now(datetime.UTC).timestamp()))
    canonical_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signing_value = f"{timestamp}.{canonical_payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_value, hashlib.sha256).hexdigest()
    return {
        "X-SelfMonitor-Signature-Timestamp": timestamp,
        "X-SelfMonitor-Signature": signature,
    }


def _verify_webhook_signature(request: Request, raw_body: bytes, secret: str) -> None:
    timestamp = request.headers.get("x-selfmonitor-signature-timestamp", "").strip()
    signature = request.headers.get("x-selfmonitor-signature", "").strip()
    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature headers.")
    try:
        timestamp_value = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature timestamp.") from exc
    now_ts = int(datetime.datetime.now(datetime.UTC).timestamp())
    if abs(now_ts - timestamp_value) > AUTH_SECURITY_ALERT_WEBHOOK_SIGNATURE_TTL_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook signature timestamp is expired.")
    signing_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")


def _serialize_delivery_item(value: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, datetime.datetime):
            payload[key] = item.isoformat()
        elif isinstance(item, dict):
            payload[key] = _serialize_delivery_item(item)
        elif isinstance(item, list):
            payload[key] = [
                _serialize_delivery_item(list_item) if isinstance(list_item, dict) else list_item
                for list_item in item
            ]
        else:
            payload[key] = item
    return payload


def _to_security_push_token_item(push_token: str, record: Dict[str, Any]) -> SecurityPushTokenItem:
    return SecurityPushTokenItem(
        push_token=push_token,
        provider=_normalize_push_provider(str(record.get("provider", "expo"))),
        registered_at=_to_utc_datetime(record.get("registered_at")) or datetime.datetime.now(datetime.UTC),
        last_used_at=_to_utc_datetime(record.get("last_used_at")),
        revoked_at=_to_utc_datetime(record.get("revoked_at")),
    )


def _build_security_alert_signal(email: str, event: SecurityEvent) -> Optional[Dict[str, str]]:
    event_type = event.event_type
    if event_type == "auth.account_lockdown_activated":
        return {
            "key": "account_lockdown_activated",
            "severity": "critical",
            "title": "Emergency lockdown activated",
            "message": "Emergency lock mode was activated for your account. Review account activity immediately.",
        }
    if event_type == "auth.login_blocked_locked":
        return {
            "key": "login_blocked_locked",
            "severity": "critical",
            "title": "Login blocked due to lockout",
            "message": "A login attempt was blocked because your account is currently locked.",
        }
    if event_type == "auth.login_failed":
        raw_attempts = event.details.get("failed_attempts", 0)
        try:
            failed_attempts = int(raw_attempts)
        except (TypeError, ValueError):
            failed_attempts = 0
        if failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            return {
                "key": "failed_login_lock_threshold",
                "severity": "critical",
                "title": "Failed login threshold reached",
                "message": (
                    f"{failed_attempts} failed logins were detected and account lockout policy has been triggered."
                ),
            }
        if failed_attempts >= max(3, MAX_FAILED_LOGIN_ATTEMPTS - 1):
            return {
                "key": "failed_login_spike",
                "severity": "attention",
                "title": "Failed login spike detected",
                "message": f"{failed_attempts} failed logins were detected in a short period.",
            }
        return None
    if event_type == "auth.login_succeeded":
        now_utc = datetime.datetime.now(datetime.UTC)
        cutoff = now_utc - datetime.timedelta(minutes=60)
        recent_success = [
            item
            for item in security_events_by_user.get(email, deque())
            if item.event_type == "auth.login_succeeded" and item.occurred_at >= cutoff
        ]
        distinct_ips = {item.ip for item in recent_success if item.ip}
        distinct_agents = {item.user_agent for item in recent_success if item.user_agent}
        if len(distinct_ips) > 1:
            return {
                "key": "multiple_login_ips_60m",
                "severity": "attention",
                "title": "New login IP detected",
                "message": f"{len(distinct_ips)} different IP addresses were used for logins in the last hour.",
            }
        if len(distinct_agents) > 1:
            return {
                "key": "multiple_login_devices_60m",
                "severity": "attention",
                "title": "New device fingerprint detected",
                "message": (
                    f"{len(distinct_agents)} different device fingerprints were used for logins in the last hour."
                ),
            }
        return None
    return None


def _is_alert_in_cooldown(email: str, alert_key: str, now_utc: datetime.datetime) -> bool:
    user_cooldowns = security_alert_cooldowns_by_user[email]
    cutoff = now_utc - datetime.timedelta(minutes=AUTH_SECURITY_ALERT_COOLDOWN_MINUTES)
    for key, timestamp in list(user_cooldowns.items()):
        if timestamp < cutoff:
            user_cooldowns.pop(key, None)
    previous = user_cooldowns.get(alert_key)
    if previous and previous >= cutoff:
        return True
    user_cooldowns[alert_key] = now_utc
    return False


def _post_json_with_retry_extended(
    url: str,
    payload: Any,
    *,
    headers: Optional[Dict[str, str]] = None,
) -> tuple[str, str, Optional[Any]]:
    attempts = max(AUTH_SECURITY_ALERT_DELIVERY_RETRY_ATTEMPTS, 1)
    last_detail = "Dispatch failed."
    response_payload: Optional[Any] = None
    for attempt in range(attempts):
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=AUTH_SECURITY_ALERT_DISPATCH_TIMEOUT_SECONDS,
            )
            if 200 <= response.status_code < 300:
                try:
                    response_payload = response.json()
                except Exception:
                    response_payload = None
                return "sent", f"HTTP {response.status_code}", response_payload
            last_detail = f"HTTP {response.status_code}"
        except Exception as exc:  # pragma: no cover - network error branch
            last_detail = _truncate_text(str(exc))
        if attempt < attempts - 1:
            backoff_seconds = AUTH_SECURITY_ALERT_DELIVERY_RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
            time.sleep(backoff_seconds)
    return "failed", last_detail, response_payload


def _post_json_with_retry(url: str, payload: Any) -> tuple[str, str]:
    status_text, detail, _response_payload = _post_json_with_retry_extended(url, payload)
    return status_text, detail


def _collect_active_push_tokens(email: str, provider: str) -> list[str]:
    normalized_email = _normalize_email(email)
    normalized_provider = _normalize_push_provider(provider)
    records = security_push_tokens_by_user.get(normalized_email, {})
    tokens: list[str] = []
    for token_value, record in records.items():
        if _normalize_push_provider(str(record.get("provider", "expo"))) != normalized_provider:
            continue
        if record.get("revoked_at"):
            continue
        if token_value:
            tokens.append(token_value)
    return tokens


def _touch_push_tokens(email: str, provider: str, token_values: list[str]) -> None:
    if not token_values:
        return
    normalized_email = _normalize_email(email)
    normalized_provider = _normalize_push_provider(provider)
    now_utc = datetime.datetime.now(datetime.UTC)
    user_tokens = security_push_tokens_by_user.get(normalized_email, {})
    for token_value in token_values:
        record = user_tokens.get(token_value)
        if not record:
            continue
        if _normalize_push_provider(str(record.get("provider", "expo"))) != normalized_provider:
            continue
        if record.get("revoked_at"):
            continue
        record["last_used_at"] = now_utc


def _dispatch_security_alert_via_webhook(
    *,
    url: str,
    payload: Dict[str, Any],
) -> Dict[str, str]:
    if not url:
        return {"status": "failed", "detail": "Webhook dispatch URL is not configured."}
    headers = _build_webhook_signature_headers(payload, AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET)
    if headers:
        status_text, detail, _response_payload = _post_json_with_retry_extended(url, payload, headers=headers)
        return {"status": status_text, "detail": detail}
    status_text, detail = _post_json_with_retry(url, payload)
    return {"status": status_text, "detail": detail}


def _dispatch_security_alert_email(
    *,
    email: str,
    event: SecurityEvent,
    signal: Dict[str, str],
) -> Dict[str, Any]:
    if not AUTH_SECURITY_ALERT_EMAIL_ENABLED:
        return {"status": "skipped", "detail": "Email alerts disabled."}
    provider = AUTH_SECURITY_ALERT_EMAIL_PROVIDER
    subject = f"[{signal['severity'].upper()}] {signal['title']}"
    dispatch_id = str(signal.get("dispatch_id", ""))
    base_payload = {
        "to": email,
        "from": AUTH_SECURITY_ALERT_EMAIL_FROM,
        "subject": subject,
        "message": signal["message"],
        "dispatch_id": dispatch_id,
        "event": {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "occurred_at": event.occurred_at.isoformat(),
            "ip": event.ip,
            "user_agent": event.user_agent,
        },
        "severity": signal["severity"],
    }
    if provider == "webhook":
        return _dispatch_security_alert_via_webhook(
            url=AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL,
            payload=base_payload,
        )
    if provider == "sendgrid":
        if not AUTH_SECURITY_ALERT_SENDGRID_API_KEY:
            return {"status": "failed", "detail": "SendGrid API key is not configured."}
        sendgrid_payload = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "subject": subject,
                    "custom_args": {
                        "dispatch_id": dispatch_id,
                        "alert_key": signal["key"],
                        "event_type": event.event_type,
                    },
                }
            ],
            "from": {"email": AUTH_SECURITY_ALERT_EMAIL_FROM},
            "content": [{"type": "text/plain", "value": signal["message"]}],
        }
        headers = {
            "Authorization": f"Bearer {AUTH_SECURITY_ALERT_SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        }
        status_text, detail, _response_payload = _post_json_with_retry_extended(
            AUTH_SECURITY_ALERT_SENDGRID_API_URL,
            sendgrid_payload,
            headers=headers,
        )
        return {"status": status_text, "detail": detail}
    return {"status": "failed", "detail": "Unsupported email alert provider."}


def _dispatch_security_alert_push(
    *,
    email: str,
    event: SecurityEvent,
    signal: Dict[str, str],
) -> Dict[str, Any]:
    if not AUTH_SECURITY_ALERT_PUSH_ENABLED:
        return {"status": "skipped", "detail": "Push alerts disabled."}
    provider = AUTH_SECURITY_ALERT_PUSH_PROVIDER
    title_prefix = AUTH_SECURITY_ALERT_PUSH_TITLE_PREFIX or "SelfMonitor Security"
    dispatch_id = str(signal.get("dispatch_id", ""))
    base_payload = {
        "recipient_email": email,
        "title": f"{title_prefix}: {signal['title']}",
        "body": signal["message"],
        "severity": signal["severity"],
        "dispatch_id": dispatch_id,
        "route": "/security",
        "data": {
            "dispatch_id": dispatch_id,
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "occurred_at": event.occurred_at.isoformat(),
        },
    }
    if provider == "webhook":
        return _dispatch_security_alert_via_webhook(
            url=AUTH_SECURITY_ALERT_PUSH_DISPATCH_URL,
            payload=base_payload,
        )
    if provider == "expo":
        expo_tokens = _collect_active_push_tokens(email, "expo")
        if not expo_tokens:
            return {"status": "failed", "detail": "No active Expo push tokens registered."}
        messages = [
            {
                "to": token_value,
                "title": base_payload["title"],
                "body": base_payload["body"],
                "sound": "default",
                "data": base_payload["data"],
            }
            for token_value in expo_tokens
        ]
        headers = {
            "Accept": "application/json",
            "Accept-encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }
        request_payload: Dict[str, Any] | list[Dict[str, Any]]
        if len(messages) == 1:
            request_payload = messages[0]
        else:
            request_payload = messages
        status_text, detail, response_payload = _post_json_with_retry_extended(
            AUTH_SECURITY_ALERT_EXPO_PUSH_API_URL,
            request_payload,
            headers=headers,
        )
        provider_message_id = None
        if isinstance(response_payload, dict):
            items = response_payload.get("data")
            if isinstance(items, list):
                ticket_ids = [
                    str(item.get("id"))
                    for item in items
                    if isinstance(item, dict) and item.get("status") == "ok" and item.get("id")
                ]
                if ticket_ids:
                    provider_message_id = ",".join(ticket_ids[:5])
            elif isinstance(items, dict) and items.get("status") == "ok" and items.get("id"):
                provider_message_id = str(items.get("id"))
        response_payload = {
            "status": status_text,
            "detail": detail,
        }
        if provider_message_id:
            response_payload["provider_message_id"] = provider_message_id
        if status_text == "sent":
            _touch_push_tokens(email, "expo", expo_tokens)
        return response_payload
    if provider == "fcm":
        fcm_tokens = _collect_active_push_tokens(email, "fcm")
        if not fcm_tokens:
            return {"status": "failed", "detail": "No active FCM push tokens registered."}
        if not AUTH_SECURITY_ALERT_FCM_SERVER_KEY:
            return {"status": "failed", "detail": "FCM server key is not configured."}
        fcm_payload = {
            "registration_ids": fcm_tokens,
            "notification": {
                "title": base_payload["title"],
                "body": base_payload["body"],
            },
            "data": base_payload["data"],
        }
        headers = {
            "Authorization": f"key={AUTH_SECURITY_ALERT_FCM_SERVER_KEY}",
            "Content-Type": "application/json",
        }
        status_text, detail, response_payload = _post_json_with_retry_extended(
            AUTH_SECURITY_ALERT_FCM_API_URL,
            fcm_payload,
            headers=headers,
        )
        provider_message_id = None
        if isinstance(response_payload, dict):
            results = response_payload.get("results")
            if isinstance(results, list):
                message_ids = [
                    str(item.get("message_id"))
                    for item in results
                    if isinstance(item, dict) and item.get("message_id")
                ]
                if message_ids:
                    provider_message_id = ",".join(message_ids[:5])
        response_payload = {
            "status": status_text,
            "detail": detail,
        }
        if provider_message_id:
            response_payload["provider_message_id"] = provider_message_id
        if status_text == "sent":
            _touch_push_tokens(email, "fcm", fcm_tokens)
        return response_payload
    return {"status": "failed", "detail": "Unsupported push alert provider."}


def _dispatch_security_alerts_for_event(email: str, event: SecurityEvent) -> Optional[Dict[str, Any]]:
    if not AUTH_SECURITY_ALERTS_ENABLED:
        return None
    signal = _build_security_alert_signal(email, event)
    if not signal:
        return None
    now_utc = datetime.datetime.now(datetime.UTC)
    dispatch_id = str(uuid.uuid4())
    signal["dispatch_id"] = dispatch_id
    alert_key = signal["key"]
    if _is_alert_in_cooldown(email, alert_key, now_utc):
        delivery = {
            "dispatch_id": dispatch_id,
            "alert_key": alert_key,
            "severity": signal["severity"],
            "status": "throttled",
            "reason": "Cooldown is active for this risk signal.",
            "occurred_at": now_utc.isoformat(),
        }
        security_alert_dispatch_log[email].append(delivery)
        security_alert_deliveries_by_id[dispatch_id] = delivery
        return delivery

    email_delivery = _dispatch_security_alert_email(email=email, event=event, signal=signal)
    push_delivery = _dispatch_security_alert_push(email=email, event=event, signal=signal)
    delivery_status = "dispatched"
    if (
        email_delivery.get("status") not in {"sent", "skipped"}
        and push_delivery.get("status") not in {"sent", "skipped"}
    ):
        delivery_status = "failed"
    delivery = {
        "dispatch_id": dispatch_id,
        "email": email,
        "alert_key": alert_key,
        "severity": signal["severity"],
        "title": signal["title"],
        "status": delivery_status,
        "channels": {
            "email": email_delivery,
            "push": push_delivery,
        },
        "occurred_at": now_utc.isoformat(),
    }
    security_alert_dispatch_log[email].append(delivery)
    security_alert_deliveries_by_id[dispatch_id] = delivery
    return delivery


def _append_security_event(
    *,
    email: str,
    event_type: str,
    request: Optional[Request],
    details: Optional[Dict[str, Any]] = None,
) -> None:
    normalized_email = _normalize_email(email)
    if normalized_email not in fake_users_db:
        return
    event = SecurityEvent(
        event_type=event_type,
        occurred_at=datetime.datetime.now(datetime.UTC),
        ip=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        details=details or {},
    )
    security_events_by_user[normalized_email].append(event)
    try:
        alert_delivery = _dispatch_security_alerts_for_event(normalized_email, event)
        if alert_delivery:
            event.details["risk_alert_delivery"] = alert_delivery
    except Exception as exc:  # pragma: no cover - defensive guard
        event.details["risk_alert_delivery_error"] = _truncate_text(str(exc))
    _persist_runtime_state_snapshot()


def _validate_password_policy(password: str, email: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters.",
        )
    if not any(ch.isalpha() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include at least one letter.",
        )
    local_part = _normalize_email(email).split("@", 1)[0]
    lowered = password.lower()
    if local_part and local_part in lowered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must not include email local part.",
        )
    if lowered in {"password", "password123", "qwerty123", "12345678"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common.",
        )


def _has_accepted_current_legal(user_record: Dict[str, Any]) -> bool:
    user_data = user_record.get("user_data", {})
    accepted_version = str(user_data.get("legal_accepted_version") or "").strip()
    accepted_at = _to_utc_datetime(user_data.get("legal_accepted_at"))
    return accepted_version == AUTH_LEGAL_CURRENT_VERSION and accepted_at is not None


def _extract_totp_code(scopes: list[str]) -> Optional[str]:
    for scope_item in scopes:
        if scope_item.startswith("totp:"):
            code = scope_item.split(":", 1)[1].strip()
            if code:
                return code
    return None


def _cleanup_login_ip_bucket(ip: str, now_utc: datetime.datetime) -> deque[datetime.datetime]:
    bucket = login_attempts_by_ip[ip]
    cutoff = now_utc - datetime.timedelta(seconds=LOGIN_IP_WINDOW_SECONDS)
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    return bucket


def _is_ip_rate_limited(ip: str, now_utc: datetime.datetime) -> bool:
    bucket = _cleanup_login_ip_bucket(ip, now_utc)
    if len(bucket) >= LOGIN_IP_MAX_ATTEMPTS:
        return True
    bucket.append(now_utc)
    return False


def _is_account_locked(user_record: Dict[str, Any], now_utc: datetime.datetime) -> bool:
    locked_until = _to_utc_datetime(user_record["user_data"].get("locked_until"))
    if not locked_until:
        return False
    if locked_until <= now_utc:
        user_record["user_data"]["failed_login_attempts"] = 0
        user_record["user_data"]["locked_until"] = None
        return False
    return True


def _register_failed_login_attempt(
    *,
    email: str,
    request: Optional[Request],
    now_utc: datetime.datetime,
    reason: str,
) -> None:
    user_record = get_user_record(email)
    if not user_record:
        return
    failed_attempts = int(user_record["user_data"].get("failed_login_attempts", 0)) + 1
    user_record["user_data"]["failed_login_attempts"] = failed_attempts
    details: Dict[str, Any] = {"reason": reason, "failed_attempts": failed_attempts}
    if failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        locked_until = now_utc + datetime.timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
        user_record["user_data"]["locked_until"] = locked_until
        details["locked_until"] = locked_until.isoformat()
    _append_security_event(
        email=email,
        event_type="auth.login_failed",
        request=request,
        details=details,
    )


def _reset_failed_login_state(user_record: Dict[str, Any]) -> None:
    user_record["user_data"]["failed_login_attempts"] = 0
    user_record["user_data"]["locked_until"] = None


def _revoke_refresh_token_jti(jti: str, *, reason: str) -> None:
    if not jti:
        return
    revoked_refresh_tokens.add(jti)
    session = refresh_token_sessions.get(jti)
    if not session:
        return
    session["revoked_at"] = datetime.datetime.now(datetime.UTC)
    session["revocation_reason"] = reason
    email = _normalize_email(str(session.get("email", "")))
    if email:
        refresh_tokens_by_user[email].discard(jti)
    _persist_runtime_state_snapshot()


def _revoke_all_refresh_tokens_for_user(email: str, *, reason: str) -> None:
    normalized_email = _normalize_email(email)
    for jti in list(refresh_tokens_by_user.get(normalized_email, set())):
        _revoke_refresh_token_jti(jti, reason=reason)
    refresh_tokens_by_user.pop(normalized_email, None)


def _issue_token_pair(email: str, request: Optional[Request]) -> Token:
    normalized_email = _normalize_email(email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    user = User(**user_record["user_data"])
    token_version = int(user_record["user_data"].get("token_version", 0))

    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": normalized_email, **build_access_claims(user, token_version)},
        expires_delta=access_token_expires,
    )
    refresh_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token(
        data={
            "sub": normalized_email,
            "jti": refresh_jti,
            "tv": token_version,
        },
        expires_delta=refresh_token_expires,
    )
    refresh_token_sessions[refresh_jti] = {
        "email": normalized_email,
        "issued_at": datetime.datetime.now(datetime.UTC),
        "expires_at": datetime.datetime.now(datetime.UTC) + refresh_token_expires,
        "revoked_at": None,
        "ip": request.client.host if request and request.client else None,
        "user_agent": request.headers.get("user-agent") if request else None,
    }
    refresh_tokens_by_user[normalized_email].add(refresh_jti)
    _persist_runtime_state_snapshot()
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
    )


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def create_mobile_attestation_token(*, email: str, installation_id: str) -> tuple[str, datetime.datetime]:
    normalized_email = _normalize_email(email)
    now_utc = datetime.datetime.now(datetime.UTC)
    expires_at = now_utc + datetime.timedelta(minutes=AUTH_MOBILE_ATTESTATION_TOKEN_TTL_MINUTES)
    token = jwt.encode(
        {
            "sub": normalized_email,
            "typ": "mobile_attestation",
            "iat": now_utc,
            "exp": expires_at,
            "installation_id": installation_id,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token, expires_at


def _decode_mobile_attestation_payload(token: str) -> Dict[str, Any]:
    payload = _decode_jwt_payload(token)
    if payload.get("typ") != "mobile_attestation":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile attestation token.",
        )
    return payload


def _parse_jwt_time_claim(value: Any) -> Optional[datetime.datetime]:
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(float(value), tz=datetime.UTC)
        except (ValueError, OSError):
            return None
    if isinstance(value, datetime.datetime):
        return _to_utc_datetime(value)
    return None


# --- Dependencies ---

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    payload = _decode_jwt_payload(token)
    email: Optional[str] = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("typ")
    if token_type and token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_record = get_user_record(email)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_version_claim = payload.get("tv")
    if token_version_claim is not None:
        try:
            token_version = int(token_version_claim)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        current_token_version = int(user_record["user_data"].get("token_version", 0))
        if token_version != current_token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is no longer valid",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user = User(**user_record["user_data"])
    return user


async def get_current_active_user(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user", headers={"WWW-Authenticate": "Bearer"})
    if AUTH_REQUIRE_LEGAL_ACCEPTANCE and not request.url.path.startswith("/legal"):
        user_record = get_user_record(current_user.email)
        if not user_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        if not _has_accepted_current_legal(user_record):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Legal terms acceptance is required before continuing.",
            )
    return current_user


async def require_admin(current_user: Annotated[User, Depends(get_current_active_user)]):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    if REQUIRE_ADMIN_2FA and not current_user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin action requires 2FA to be enabled.",
        )
    return current_user


async def require_recent_auth(token: Annotated[str, Depends(oauth2_scheme)]) -> None:
    payload = _decode_jwt_payload(token)
    issued_at = _parse_jwt_time_claim(payload.get("iat"))
    if not issued_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Step-up authentication required.",
        )
    age_minutes = (datetime.datetime.now(datetime.UTC) - issued_at).total_seconds() / 60
    if age_minutes > STEP_UP_MAX_AGE_MINUTES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Step-up authentication required.",
        )


async def require_mobile_attestation(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    if not AUTH_MOBILE_ATTESTATION_ENABLED:
        return
    attestation_token = request.headers.get(MOBILE_ATTESTATION_HEADER, "").strip()
    installation_header = request.headers.get(MOBILE_INSTALLATION_ID_HEADER, "").strip()
    if not attestation_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mobile attestation token is required.",
        )
    if not installation_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mobile installation id header is required.",
        )
    payload = _decode_mobile_attestation_payload(attestation_token)
    if _normalize_email(str(payload.get("sub", ""))) != _normalize_email(current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mobile attestation subject mismatch.",
        )
    token_installation_id = str(payload.get("installation_id", "")).strip()
    if not token_installation_id or token_installation_id != installation_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mobile attestation installation mismatch.",
        )

# --- Endpoints ---

@app.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
):
    normalized_email = _normalize_email(form_data.username)
    if normalized_email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    _validate_password_policy(form_data.password, normalized_email)

    user_record = _build_user_record(
        email=normalized_email,
        hashed_password=get_password_hash(form_data.password),
        is_admin=False,
        email_verified=False,
    )
    fake_users_db[normalized_email] = user_record
    _append_security_event(
        email=normalized_email,
        event_type="account.registered",
        request=request,
    )
    return User(**user_record["user_data"])


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
):
    now_utc = datetime.datetime.now(datetime.UTC)
    client_ip = request.client.host if request.client and request.client.host else "unknown"
    if _is_ip_rate_limited(client_ip, now_utc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts from this IP. Please retry later.",
        )

    normalized_email = _normalize_email(form_data.username)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise _build_login_error()

    if _is_account_locked(user_record, now_utc):
        _append_security_event(
            email=normalized_email,
            event_type="auth.login_blocked_locked",
            request=request,
            details={"locked_until": str(user_record["user_data"].get("locked_until"))},
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to failed login attempts. Try again later.",
        )

    if not verify_password(form_data.password, user_record["hashed_password"]):
        _register_failed_login_attempt(
            email=normalized_email,
            request=request,
            now_utc=now_utc,
            reason="invalid_password",
        )
        if _is_account_locked(user_record, now_utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to failed login attempts. Try again later.",
            )
        raise _build_login_error()

    user = User(**user_record["user_data"])
    if not user.is_active:
        _append_security_event(
            email=normalized_email,
            event_type="auth.login_rejected_inactive",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

    if REQUIRE_VERIFIED_EMAIL_FOR_LOGIN and not user.email_verified:
        _append_security_event(
            email=normalized_email,
            event_type="auth.login_rejected_unverified_email",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required before login.",
        )

    if user.is_two_factor_enabled:
        totp_code = _extract_totp_code(form_data.scopes)
        if not totp_code:
            _register_failed_login_attempt(
                email=normalized_email,
                request=request,
                now_utc=now_utc,
                reason="missing_2fa_code",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA code required in 'scope' field (e.g., 'totp:123456')",
            )

        secret = user_record["user_data"].get("two_factor_secret")
        if not isinstance(secret, str) or not secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA is enabled but secret is not configured.",
            )

        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code, valid_window=TOTP_VALID_WINDOW_STEPS):
            _register_failed_login_attempt(
                email=normalized_email,
                request=request,
                now_utc=now_utc,
                reason="invalid_2fa_code",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

    _reset_failed_login_state(user_record)
    user_record["user_data"]["last_login_at"] = now_utc
    _append_security_event(
        email=normalized_email,
        event_type="auth.login_succeeded",
        request=request,
    )
    return _issue_token_pair(normalized_email, request)


def _decode_refresh_token_payload(refresh_token: str) -> Dict[str, Any]:
    payload = _decode_jwt_payload(refresh_token)
    if payload.get("typ") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    return payload


@app.post("/token/refresh", response_model=Token)
async def refresh_access_token(payload: RefreshTokenRequest, request: Request):
    refresh_payload = _decode_refresh_token_payload(payload.refresh_token)
    normalized_email = _normalize_email(str(refresh_payload.get("sub", "")))
    jti = str(refresh_payload.get("jti", ""))
    token_version_claim = refresh_payload.get("tv")

    if not normalized_email or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if jti in revoked_refresh_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token already revoked")

    session = refresh_token_sessions.get(jti)
    if not session or session.get("revoked_at") is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not active")
    if _normalize_email(str(session.get("email", ""))) != normalized_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token mismatch")

    user_record = get_user_record(normalized_email)
    if not user_record:
        _revoke_refresh_token_jti(jti, reason="user_missing")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    current_token_version = int(user_record["user_data"].get("token_version", 0))
    try:
        refresh_token_version = int(token_version_claim) if token_version_claim is not None else -1
    except (TypeError, ValueError):
        refresh_token_version = -1
    if refresh_token_version != current_token_version:
        _revoke_refresh_token_jti(jti, reason="token_version_mismatch")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is no longer valid")

    if not bool(user_record["user_data"].get("is_active", True)):
        _revoke_refresh_token_jti(jti, reason="inactive_user")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    if REQUIRE_VERIFIED_EMAIL_FOR_LOGIN and not bool(user_record["user_data"].get("email_verified", False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email verification required.")

    _revoke_refresh_token_jti(jti, reason="rotated")
    _append_security_event(
        email=normalized_email,
        event_type="auth.refresh_succeeded",
        request=request,
    )
    return _issue_token_pair(normalized_email, request)


@app.post("/token/revoke")
async def revoke_refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
):
    refresh_payload = _decode_refresh_token_payload(payload.refresh_token)
    normalized_email = _normalize_email(str(refresh_payload.get("sub", "")))
    if normalized_email != _normalize_email(current_user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke token for another user")
    jti = str(refresh_payload.get("jti", ""))
    _revoke_refresh_token_jti(jti, reason="manual_revoke")
    _append_security_event(
        email=normalized_email,
        event_type="auth.refresh_revoked",
        request=request,
    )
    return {"message": "Refresh token revoked."}


@app.post("/password/change")
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
):
    normalized_email = _normalize_email(current_user.email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_password(payload.current_password, user_record["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must differ from current")

    _validate_password_policy(payload.new_password, normalized_email)
    user_record["hashed_password"] = get_password_hash(payload.new_password)
    user_record["user_data"]["password_changed_at"] = datetime.datetime.now(datetime.UTC)
    user_record["user_data"]["token_version"] = int(user_record["user_data"].get("token_version", 0)) + 1
    _reset_failed_login_state(user_record)
    _revoke_all_refresh_tokens_for_user(normalized_email, reason="password_changed")
    _append_security_event(
        email=normalized_email,
        event_type="auth.password_changed",
        request=request,
    )
    return {"message": "Password changed successfully. Please sign in again."}


@app.post("/verify-email/request", response_model=EmailVerificationChallengeResponse)
async def request_email_verification(
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
):
    normalized_email = _normalize_email(current_user.email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if bool(user_record["user_data"].get("email_verified", False)):
        return EmailVerificationChallengeResponse(
            message="Email is already verified.",
            code_sent=True,
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=EMAIL_VERIFICATION_CODE_TTL_MINUTES),
            debug_code=None,
        )

    verification_code = "".join(str(secrets.randbelow(10)) for _ in range(6))
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=EMAIL_VERIFICATION_CODE_TTL_MINUTES
    )
    user_record["user_data"]["email_verification_code_hash"] = _hash_short_code(verification_code)
    user_record["user_data"]["email_verification_expires_at"] = expires_at
    user_record["user_data"]["email_verification_attempts"] = 0
    _append_security_event(
        email=normalized_email,
        event_type="auth.email_verification_requested",
        request=request,
    )
    return EmailVerificationChallengeResponse(
        message="Email verification challenge generated.",
        code_sent=True,
        expires_at=expires_at,
        debug_code=verification_code if EMAIL_VERIFICATION_DEBUG_RETURN_CODE else None,
    )


@app.post("/verify-email/confirm", response_model=EmailVerificationConfirmResponse)
async def confirm_email_verification(
    payload: EmailVerificationConfirmRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
):
    normalized_email = _normalize_email(current_user.email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if bool(user_record["user_data"].get("email_verified", False)):
        return EmailVerificationConfirmResponse(
            message="Email is already verified.",
            email_verified=True,
        )

    stored_hash = user_record["user_data"].get("email_verification_code_hash")
    expires_at = _to_utc_datetime(user_record["user_data"].get("email_verification_expires_at"))
    if not stored_hash or not expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification request is missing.")
    if expires_at < datetime.datetime.now(datetime.UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired.")

    attempts = int(user_record["user_data"].get("email_verification_attempts", 0))
    if attempts >= EMAIL_VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Request a new code.",
        )

    candidate_hash = _hash_short_code(payload.code.strip())
    if not hmac.compare_digest(candidate_hash, str(stored_hash)):
        attempts += 1
        user_record["user_data"]["email_verification_attempts"] = attempts
        _append_security_event(
            email=normalized_email,
            event_type="auth.email_verification_failed",
            request=request,
            details={"attempts": attempts},
        )
        if attempts >= EMAIL_VERIFICATION_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification attempts. Request a new code.",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    user_record["user_data"]["email_verified"] = True
    user_record["user_data"]["email_verification_code_hash"] = None
    user_record["user_data"]["email_verification_expires_at"] = None
    user_record["user_data"]["email_verification_attempts"] = 0
    _append_security_event(
        email=normalized_email,
        event_type="auth.email_verified",
        request=request,
    )
    return EmailVerificationConfirmResponse(
        message="Email verified successfully.",
        email_verified=True,
    )


@app.get("/legal/current", response_model=LegalPolicyCurrentResponse)
async def get_current_legal_policy():
    return LegalPolicyCurrentResponse(
        current_version=AUTH_LEGAL_CURRENT_VERSION,
        terms_url=AUTH_LEGAL_TERMS_URL,
        eula_url=AUTH_LEGAL_EULA_URL,
        requires_acceptance=AUTH_REQUIRE_LEGAL_ACCEPTANCE,
    )


@app.post("/legal/accept", response_model=LegalPolicyAcceptResponse)
async def accept_current_legal_policy(
    payload: LegalPolicyAcceptRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    user_record = get_user_record(current_user.email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    requested_version = payload.version.strip()
    if requested_version != AUTH_LEGAL_CURRENT_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Requested legal version '{requested_version}' is not current. "
                f"Current version is '{AUTH_LEGAL_CURRENT_VERSION}'."
            ),
        )
    accepted_at = datetime.datetime.now(datetime.UTC)
    user_record["user_data"]["legal_accepted_version"] = AUTH_LEGAL_CURRENT_VERSION
    user_record["user_data"]["legal_accepted_at"] = accepted_at
    _append_security_event(
        email=current_user.email,
        event_type="auth.legal_terms_accepted",
        request=request,
        details={
            "version": AUTH_LEGAL_CURRENT_VERSION,
            "source": payload.source.strip().lower(),
        },
    )
    return LegalPolicyAcceptResponse(
        message="Legal terms accepted.",
        accepted_version=AUTH_LEGAL_CURRENT_VERSION,
        accepted_at=accepted_at,
        has_accepted_current_legal=True,
    )


@app.get("/security/events", response_model=SecurityEventsResponse)
async def list_security_events(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(default=20, ge=1, le=100),
):
    normalized_email = _normalize_email(current_user.email)
    events = list(security_events_by_user.get(normalized_email, deque()))
    items = events[-limit:]
    items.reverse()
    return SecurityEventsResponse(total=len(events), items=items)


@app.get("/security/alerts/deliveries", response_model=SecurityAlertDeliveriesResponse)
async def list_security_alert_deliveries(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(default=20, ge=1, le=100),
):
    normalized_email = _normalize_email(current_user.email)
    deliveries = list(security_alert_dispatch_log.get(normalized_email, deque()))
    items = deliveries[-limit:]
    items.reverse()
    sanitized_items: list[Dict[str, Any]] = []
    for item in items:
        serialized = _serialize_delivery_item(item)
        serialized.pop("email", None)
        sanitized_items.append(serialized)
    return SecurityAlertDeliveriesResponse(total=len(deliveries), items=sanitized_items)


@app.post("/mobile/attestation/session", response_model=MobileAttestationSessionResponse)
async def issue_mobile_attestation_session(
    payload: MobileAttestationSessionRequest,
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if not AUTH_MOBILE_ATTESTATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile attestation is disabled.",
        )

    if AUTH_MOBILE_ATTESTATION_REQUIRE_RECENT_AUTH:
        jwt_payload = _decode_jwt_payload(token)
        issued_at = _parse_jwt_time_claim(jwt_payload.get("iat"))
        if not issued_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Step-up authentication required.",
            )
        age_minutes = (datetime.datetime.now(datetime.UTC) - issued_at).total_seconds() / 60
        if age_minutes > STEP_UP_MAX_AGE_MINUTES:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Step-up authentication required.",
            )

    installation_id = payload.installation_id.strip()
    if not installation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installation_id cannot be blank.")

    normalized_email = _normalize_email(current_user.email)
    attestation_token, expires_at = create_mobile_attestation_token(
        email=normalized_email,
        installation_id=installation_id,
    )
    _append_security_event(
        email=normalized_email,
        event_type="auth.mobile_attestation_issued",
        request=request,
        details={
            "installation_fingerprint": hashlib.sha256(installation_id.encode("utf-8")).hexdigest()[:16],
            "expires_at": expires_at.isoformat(),
        },
    )
    return MobileAttestationSessionResponse(
        token_type="bearer",
        attestation_token=attestation_token,
        expires_at=expires_at,
        installation_id=installation_id,
    )


def _register_push_token_for_user(
    *,
    email: str,
    payload: SecurityPushTokenRegisterRequest,
    request: Request,
    source: str,
) -> SecurityPushTokenRegisterResponse:
    normalized_email = _normalize_email(email)
    provider = _normalize_push_provider(payload.provider)
    token_value = payload.push_token.strip()
    if not token_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="push_token cannot be blank.")
    user_tokens = security_push_tokens_by_user[normalized_email]
    previous_record = user_tokens.get(token_value, {})
    user_tokens[token_value] = {
        "provider": provider,
        "registered_at": _to_utc_datetime(previous_record.get("registered_at")) or datetime.datetime.now(datetime.UTC),
        "last_used_at": _to_utc_datetime(previous_record.get("last_used_at")),
        "revoked_at": None,
    }
    active_count = len([item for item in user_tokens.values() if item.get("revoked_at") is None])
    _append_security_event(
        email=normalized_email,
        event_type="auth.push_token_registered",
        request=request,
        details={
            "provider": provider,
            "source": source,
            "token_fingerprint": hashlib.sha256(token_value.encode("utf-8")).hexdigest()[:16],
        },
    )
    return SecurityPushTokenRegisterResponse(
        message="Push token registered.",
        total_active_tokens=active_count,
    )


def _revoke_push_token_for_user(
    *,
    email: str,
    push_token: str,
    request: Request,
    source: str,
) -> SecurityPushTokenRevokeResponse:
    normalized_email = _normalize_email(email)
    user_tokens = security_push_tokens_by_user.get(normalized_email, {})
    token_value = push_token.strip()
    token_record = user_tokens.get(token_value)
    if not token_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push token not found.")
    if token_record.get("revoked_at"):
        return SecurityPushTokenRevokeResponse(message="Push token already revoked.", revoked_tokens=0)
    token_record["revoked_at"] = datetime.datetime.now(datetime.UTC)
    _append_security_event(
        email=normalized_email,
        event_type="auth.push_token_revoked",
        request=request,
        details={
            "provider": _normalize_push_provider(str(token_record.get("provider", "expo"))),
            "source": source,
            "token_fingerprint": hashlib.sha256(token_value.encode("utf-8")).hexdigest()[:16],
        },
    )
    return SecurityPushTokenRevokeResponse(message="Push token revoked.", revoked_tokens=1)


@app.post("/security/push-tokens", response_model=SecurityPushTokenRegisterResponse)
async def register_security_push_token(
    payload: SecurityPushTokenRegisterRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return _register_push_token_for_user(
        email=current_user.email,
        payload=payload,
        request=request,
        source="web",
    )


@app.post("/mobile/security/push-tokens", response_model=SecurityPushTokenRegisterResponse)
async def register_mobile_security_push_token(
    payload: SecurityPushTokenRegisterRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _mobile_attestation: None = Depends(require_mobile_attestation),
):
    return _register_push_token_for_user(
        email=current_user.email,
        payload=payload,
        request=request,
        source="mobile_attested",
    )


@app.get("/security/push-tokens", response_model=SecurityPushTokensResponse)
async def list_security_push_tokens(
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_revoked: bool = Query(default=False),
):
    normalized_email = _normalize_email(current_user.email)
    user_tokens = security_push_tokens_by_user.get(normalized_email, {})
    items: list[SecurityPushTokenItem] = []
    for token_value, record in user_tokens.items():
        if not include_revoked and record.get("revoked_at"):
            continue
        items.append(_to_security_push_token_item(token_value, record))
    items.sort(key=lambda item: item.registered_at, reverse=True)
    return SecurityPushTokensResponse(total_tokens=len(items), items=items)


@app.delete("/security/push-tokens/{push_token}", response_model=SecurityPushTokenRevokeResponse)
async def revoke_security_push_token(
    push_token: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return _revoke_push_token_for_user(
        email=current_user.email,
        push_token=push_token,
        request=request,
        source="web",
    )


@app.delete("/mobile/security/push-tokens/{push_token}", response_model=SecurityPushTokenRevokeResponse)
async def revoke_mobile_security_push_token(
    push_token: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _mobile_attestation: None = Depends(require_mobile_attestation),
):
    return _revoke_push_token_for_user(
        email=current_user.email,
        push_token=push_token,
        request=request,
        source="mobile_attested",
    )


@app.post("/security/alerts/delivery-receipts", response_model=SecurityAlertDeliveryReceiptResponse)
async def ingest_security_alert_delivery_receipt(request: Request):
    if not AUTH_SECURITY_ALERT_RECEIPTS_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alert receipts are disabled.")
    if not AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert receipt webhook secret is not configured.",
        )
    raw_body = await request.body()
    _verify_webhook_signature(request, raw_body, AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET)
    try:
        payload = SecurityAlertDeliveryReceiptRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    delivery = security_alert_deliveries_by_id.get(payload.dispatch_id)
    if not isinstance(delivery, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch id not found.")
    channels = delivery.get("channels")
    if not isinstance(channels, dict) or payload.channel not in channels:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown delivery channel.")
    channel_entry = channels.get(payload.channel)
    if not isinstance(channel_entry, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid delivery channel payload.")

    now_utc = datetime.datetime.now(datetime.UTC)
    receipt_time = _to_utc_datetime(payload.occurred_at) or now_utc
    channel_entry["receipt_status"] = payload.status
    channel_entry["receipt_at"] = receipt_time.isoformat()
    if payload.provider_message_id:
        channel_entry["provider_message_id"] = payload.provider_message_id
    if payload.reason:
        channel_entry["receipt_reason"] = payload.reason
    channel_entry["status"] = "sent" if payload.status in {"delivered", "opened", "clicked"} else "failed"

    channel_statuses = [
        str(item.get("status", "failed"))
        for item in channels.values()
        if isinstance(item, dict)
    ]
    if channel_statuses and all(status_item in {"sent", "skipped"} for status_item in channel_statuses):
        delivery["status"] = "delivered"
    elif channel_statuses and all(status_item == "failed" for status_item in channel_statuses):
        delivery["status"] = "failed"
    elif any(status_item == "sent" for status_item in channel_statuses):
        delivery["status"] = "partial_delivery"
    delivery["last_receipt_at"] = receipt_time.isoformat()

    owner_email = _normalize_email(str(delivery.get("email", "")))
    if owner_email in fake_users_db:
        _append_security_event(
            email=owner_email,
            event_type="auth.security_alert_receipt_updated",
            request=None,
            details={
                "dispatch_id": payload.dispatch_id,
                "channel": payload.channel,
                "status": payload.status,
            },
        )
    else:
        _persist_runtime_state_snapshot()
    return SecurityAlertDeliveryReceiptResponse(
        message="Delivery receipt processed.",
        dispatch_id=payload.dispatch_id,
        updated=True,
    )


@app.get("/security/state", response_model=SecurityStateResponse)
async def get_security_state(current_user: Annotated[User, Depends(get_current_active_user)]):
    normalized_email = _normalize_email(current_user.email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_data = user_record["user_data"]
    legal_accepted_version = str(user_data.get("legal_accepted_version") or "").strip() or None
    legal_accepted_at = _to_utc_datetime(user_data.get("legal_accepted_at"))
    return SecurityStateResponse(
        email=normalized_email,
        email_verified=bool(user_data.get("email_verified", False)),
        is_two_factor_enabled=bool(user_data.get("is_two_factor_enabled", False)),
        failed_login_attempts=int(user_data.get("failed_login_attempts", 0)),
        max_failed_login_attempts=MAX_FAILED_LOGIN_ATTEMPTS,
        locked_until=_to_utc_datetime(user_data.get("locked_until")),
        last_login_at=_to_utc_datetime(user_data.get("last_login_at")),
        password_changed_at=_to_utc_datetime(user_data.get("password_changed_at")),
        legal_current_version=AUTH_LEGAL_CURRENT_VERSION,
        legal_terms_url=AUTH_LEGAL_TERMS_URL,
        legal_eula_url=AUTH_LEGAL_EULA_URL,
        legal_accepted_version=legal_accepted_version,
        legal_accepted_at=legal_accepted_at,
        has_accepted_current_legal=(
            legal_accepted_version == AUTH_LEGAL_CURRENT_VERSION and legal_accepted_at is not None
        ),
    )


@app.get("/security/sessions", response_model=SecuritySessionsResponse)
async def list_security_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_revoked: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
):
    normalized_email = _normalize_email(current_user.email)
    if include_revoked:
        candidate_ids = [
            jti
            for jti, session in refresh_token_sessions.items()
            if _normalize_email(str(session.get("email", ""))) == normalized_email
        ]
    else:
        candidate_ids = list(refresh_tokens_by_user.get(normalized_email, set()))

    items: list[SecuritySessionItem] = []
    for jti in candidate_ids:
        session = refresh_token_sessions.get(jti)
        if not session:
            continue
        if not include_revoked and session.get("revoked_at") is not None:
            continue
        issued_at = _to_utc_datetime(session.get("issued_at"))
        expires_at = _to_utc_datetime(session.get("expires_at"))
        if not issued_at or not expires_at:
            continue
        items.append(
            SecuritySessionItem(
                session_id=jti,
                issued_at=issued_at,
                expires_at=expires_at,
                ip=str(session.get("ip")) if session.get("ip") else None,
                user_agent=str(session.get("user_agent")) if session.get("user_agent") else None,
                revoked_at=_to_utc_datetime(session.get("revoked_at")),
                revocation_reason=str(session.get("revocation_reason"))
                if session.get("revocation_reason")
                else None,
            )
        )

    items.sort(key=lambda item: item.issued_at, reverse=True)
    limited_items = items[:limit]
    active_sessions = len([item for item in items if item.revoked_at is None])
    return SecuritySessionsResponse(
        total_sessions=len(items),
        active_sessions=active_sessions,
        items=limited_items,
    )


@app.delete("/security/sessions/{session_id}", response_model=RevokeSessionsResponse)
async def revoke_security_session(
    session_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
):
    normalized_email = _normalize_email(current_user.email)
    session = refresh_token_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session_email = _normalize_email(str(session.get("email", "")))
    if session_email != normalized_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke another user session")

    already_revoked = session.get("revoked_at") is not None or session_id in revoked_refresh_tokens
    if already_revoked:
        return RevokeSessionsResponse(message="Session already revoked.", revoked_sessions=0)

    _revoke_refresh_token_jti(session_id, reason="manual_session_revoke")
    _append_security_event(
        email=normalized_email,
        event_type="auth.session_revoked",
        request=request,
        details={"session_id": session_id},
    )
    return RevokeSessionsResponse(message="Session revoked.", revoked_sessions=1)


@app.post("/security/sessions/revoke-all", response_model=RevokeSessionsResponse)
async def revoke_all_security_sessions(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
):
    normalized_email = _normalize_email(current_user.email)
    active_session_ids = list(refresh_tokens_by_user.get(normalized_email, set()))
    revoked_count = 0
    for jti in active_session_ids:
        session = refresh_token_sessions.get(jti)
        if session and session.get("revoked_at") is None:
            revoked_count += 1
        _revoke_refresh_token_jti(jti, reason="manual_revoke_all")
    _append_security_event(
        email=normalized_email,
        event_type="auth.sessions_revoked_all",
        request=request,
        details={"revoked_sessions": revoked_count},
    )
    return RevokeSessionsResponse(message="All sessions revoked.", revoked_sessions=revoked_count)


def _activate_lockdown_for_user(
    *,
    email: str,
    lock_minutes: int,
    request: Request,
    source: str,
) -> SecurityLockdownResponse:
    normalized_email = _normalize_email(email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if lock_minutes > AUTH_EMERGENCY_LOCKDOWN_MAX_MINUTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "lock_minutes exceeds maximum allowed "
                f"({AUTH_EMERGENCY_LOCKDOWN_MAX_MINUTES})."
            ),
        )

    now_utc = datetime.datetime.now(datetime.UTC)
    locked_until = now_utc + datetime.timedelta(minutes=lock_minutes)
    active_session_ids = list(refresh_tokens_by_user.get(normalized_email, set()))
    revoked_count = 0
    for jti in active_session_ids:
        session = refresh_token_sessions.get(jti)
        if session and session.get("revoked_at") is None:
            revoked_count += 1
        _revoke_refresh_token_jti(jti, reason="user_lockdown")

    user_record["user_data"]["locked_until"] = locked_until
    user_record["user_data"]["failed_login_attempts"] = max(
        int(user_record["user_data"].get("failed_login_attempts", 0)),
        MAX_FAILED_LOGIN_ATTEMPTS,
    )
    user_record["user_data"]["token_version"] = int(user_record["user_data"].get("token_version", 0)) + 1

    _append_security_event(
        email=normalized_email,
        event_type="auth.account_lockdown_activated",
        request=request,
        details={
            "lock_minutes": lock_minutes,
            "locked_until": locked_until.isoformat(),
            "revoked_sessions": revoked_count,
            "source": source,
        },
    )
    return SecurityLockdownResponse(
        message="Emergency security lockdown activated.",
        locked_until=locked_until,
        lock_minutes=lock_minutes,
        revoked_sessions=revoked_count,
    )


@app.post("/security/lockdown", response_model=SecurityLockdownResponse)
async def activate_security_lockdown(
    payload: SecurityLockdownRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
):
    return _activate_lockdown_for_user(
        email=current_user.email,
        lock_minutes=int(payload.lock_minutes),
        request=request,
        source="web",
    )


@app.post("/mobile/security/lockdown", response_model=SecurityLockdownResponse)
async def activate_mobile_security_lockdown(
    payload: SecurityLockdownRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
    _mobile_attestation: None = Depends(require_mobile_attestation),
):
    return _activate_lockdown_for_user(
        email=current_user.email,
        lock_minutes=int(payload.lock_minutes),
        request=request,
        source="mobile_attested",
    )


# --- 2FA Endpoints ---

@app.get("/2fa/setup")
async def setup_two_factor_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
):
    if current_user.is_two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled.")
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify email before enabling 2FA.",
        )

    secret = pyotp.random_base32()
    fake_users_db[_normalize_email(current_user.email)]["user_data"]["two_factor_secret"] = secret
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="FinTech App",
    )
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    _append_security_event(
        email=current_user.email,
        event_type="auth.2fa_setup_started",
        request=request,
    )
    return Response(content=buf.getvalue(), media_type="image/png")


@app.post("/2fa/verify")
async def verify_two_factor_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
    totp_code: str = Query(..., description="The 6-digit code from the authenticator app."),
):
    normalized_email = _normalize_email(current_user.email)
    user_record = fake_users_db[normalized_email]
    secret = user_record["user_data"].get("two_factor_secret")
    if not secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /2fa/setup first.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(totp_code, valid_window=TOTP_VALID_WINDOW_STEPS):
        _append_security_event(
            email=normalized_email,
            event_type="auth.2fa_verify_failed",
            request=request,
        )
        raise HTTPException(status_code=400, detail="Invalid code.")

    user_record["user_data"]["is_two_factor_enabled"] = True
    user_record["user_data"]["token_version"] = int(user_record["user_data"].get("token_version", 0)) + 1
    _revoke_all_refresh_tokens_for_user(normalized_email, reason="2fa_enabled")
    _append_security_event(
        email=normalized_email,
        event_type="auth.2fa_enabled",
        request=request,
    )
    return {"message": "2FA enabled successfully."}


@app.delete("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_two_factor_auth(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _fresh_auth: None = Depends(require_recent_auth),
    totp_code: Optional[str] = Query(default=None, description="Current TOTP code to disable 2FA."),
):
    normalized_email = _normalize_email(current_user.email)
    user_record = fake_users_db[normalized_email]
    if not current_user.is_two_factor_enabled:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if not totp_code:
        raise HTTPException(status_code=400, detail="totp_code is required to disable 2FA.")

    secret = user_record["user_data"].get("two_factor_secret")
    totp = pyotp.TOTP(str(secret or ""))
    if not secret or not totp.verify(totp_code, valid_window=TOTP_VALID_WINDOW_STEPS):
        _append_security_event(
            email=normalized_email,
            event_type="auth.2fa_disable_failed",
            request=request,
        )
        raise HTTPException(status_code=400, detail="Invalid code.")

    user_record["user_data"]["is_two_factor_enabled"] = False
    user_record["user_data"]["two_factor_secret"] = None
    user_record["user_data"]["token_version"] = int(user_record["user_data"].get("token_version", 0)) + 1
    _revoke_all_refresh_tokens_for_user(normalized_email, reason="2fa_disabled")
    _append_security_event(
        email=normalized_email,
        event_type="auth.2fa_disabled",
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user


@app.post("/users/{user_email}/deactivate", response_model=User)
async def deactivate_user(
    user_email: EmailStr,
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    _fresh_auth: None = Depends(require_recent_auth),
):
    normalized_email = _normalize_email(str(user_email))
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not bool(user_record["user_data"].get("is_active", True)):
        return User(**user_record["user_data"])

    user_record["user_data"]["is_active"] = False
    user_record["user_data"]["token_version"] = int(user_record["user_data"].get("token_version", 0)) + 1
    _revoke_all_refresh_tokens_for_user(normalized_email, reason="admin_deactivated")
    _append_security_event(
        email=normalized_email,
        event_type="account.deactivated_by_admin",
        request=request,
        details={"actor": admin_user.email},
    )
    return User(**user_record["user_data"])

