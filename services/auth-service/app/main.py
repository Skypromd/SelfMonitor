from collections import defaultdict, deque
from datetime import timedelta
from typing import Annotated, Any, Dict, Optional
import datetime
import hashlib
import hmac
import io
import os
import secrets
import uuid

from fastapi import FastAPI, Depends, HTTPException, status, Response, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
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


def get_user_record(email: str) -> Optional[Dict[str, Any]]:
    return fake_users_db.get(_normalize_email(email))


def get_user(email: str) -> Optional[User]:
    user_record = get_user_record(email)
    if not user_record:
        return None
    return User(**user_record["user_data"])


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


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user", headers={"WWW-Authenticate": "Bearer"})
    return current_user


async def require_admin(current_user: Annotated[User, Depends(get_current_active_user)]):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

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
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
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
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
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


@app.get("/security/state", response_model=SecurityStateResponse)
async def get_security_state(current_user: Annotated[User, Depends(get_current_active_user)]):
    normalized_email = _normalize_email(current_user.email)
    user_record = get_user_record(normalized_email)
    if not user_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_data = user_record["user_data"]
    return SecurityStateResponse(
        email=normalized_email,
        email_verified=bool(user_data.get("email_verified", False)),
        is_two_factor_enabled=bool(user_data.get("is_two_factor_enabled", False)),
        failed_login_attempts=int(user_data.get("failed_login_attempts", 0)),
        max_failed_login_attempts=MAX_FAILED_LOGIN_ATTEMPTS,
        locked_until=_to_utc_datetime(user_data.get("locked_until")),
        last_login_at=_to_utc_datetime(user_data.get("last_login_at")),
        password_changed_at=_to_utc_datetime(user_data.get("password_changed_at")),
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
    current_user: Annotated[User, Depends(get_current_active_user)],
    request: Request,
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

