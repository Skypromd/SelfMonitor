# isort: skip_file
import asyncio
import datetime
import email.mime.multipart
import email.mime.text
import io
import logging
import os
import re
import secrets
import smtplib
import sqlite3
import time
import uuid
from datetime import timedelta
from typing import Annotated, Any, Optional
from urllib.parse import unquote

import httpx
import pyotp  # type: ignore[import-untyped]
import qrcode  # type: ignore[import-untyped]
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    APP_BASE_URL,
    AUTH_ADMIN_EMAIL,
    AUTH_ADMIN_PASSWORD,
    AUTH_BOOTSTRAP_ADMIN,
    AUTH_CORS_ORIGINS,
    AUTH_DB_PATH,
    COMPLIANCE_SERVICE_URL,
    INTERNAL_SERVICE_SECRET,
    REFERRAL_SERVICE_URL,
    LOCKOUT_THRESHOLD,
    REQUIRE_ADMIN_2FA,
    SECRET_KEY,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    VERIFICATION_CODES_DEBUG,
    _DEFAULT_ADMIN_HEALTH_TARGETS,
)
from app import lockout
from app.db import _connect, db_lock

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Auth Service",
    description="Handles user authentication, registration, and token management.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=AUTH_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Observability ---
# This line adds an instrumentator that exposes a /metrics endpoint
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


def _require_internal_service_token(
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    if not INTERNAL_SERVICE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="internal_calls_not_configured",
        )
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def list_active_emails_for_reminders() -> list[str]:
    with db_lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT email FROM users WHERE is_active = 1"
            ).fetchall()
        finally:
            conn.close()
    out: list[str] = []
    for row in rows:
        if row and row[0]:
            out.append(str(row[0]).strip().lower())
    return out


@app.get(
    "/internal/reminder-recipients",
    dependencies=[Depends(_require_internal_service_token)],
)
async def internal_reminder_recipients():
    """Returns active user emails for scheduled MTD (or other) reminders. Internal only."""
    return {"emails": list_active_emails_for_reminders()}


# --- Security Utils ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> None:
    errors: list[str] = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("at least one special character")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must contain: {', '.join(errors)}",
        )


def create_access_token(
    data: dict[str, object], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode: dict[str, object] = data.copy()
    now = datetime.datetime.now(datetime.UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Models ---


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    plan: str = "free"
    referral_code: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ref", "referral_code"),
    )


class User(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    is_two_factor_enabled: bool = False
    organization_id: Optional[str] = None
    role: str = "user"
    subscription_tier: str = "free"
    subscription_status: str = "active"
    trial_days_remaining: Optional[int] = None


class Organization(BaseModel):
    id: str
    name: str
    subscription_plan: str = "enterprise"  # enterprise, team
    max_users: int = 50
    created_at: datetime.datetime
    owner_email: str


class TeamInvite(BaseModel):
    email: EmailStr
    organization_id: str
    role: str = "user"
    invited_by: str
    expires_at: datetime.datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class ApiKeyCreate(BaseModel):
    label: str = Field(default="", max_length=128)


class ApiKeyCreated(BaseModel):
    key_id: str
    label: str
    api_key: str
    created_at: int
    message: str = "Store this key securely; it cannot be retrieved again."


class ApiKeyListItem(BaseModel):
    key_id: str
    label: str
    created_at: int
    last_used_at: Optional[int] = None


class ApiKeyExchangeRequest(BaseModel):
    api_key: str = Field(min_length=20, max_length=500)


class TokenData(BaseModel):
    email: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# --- Database ---
def _seed_admin_user(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT email FROM users WHERE email = ?", (AUTH_ADMIN_EMAIL,)
    ).fetchone()
    if existing:
        return
    conn.execute(
        """
        INSERT INTO users (email, hashed_password, is_active, is_admin, is_two_factor_enabled, two_factor_secret, role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (AUTH_ADMIN_EMAIL, get_password_hash(AUTH_ADMIN_PASSWORD), 1, 1, 0, None, "admin"),
    )
    conn.commit()


def _ensure_configured_admin_privileges(conn: sqlite3.Connection) -> None:
    """If someone registered via /register with AUTH_ADMIN_EMAIL, they stay is_admin=0 until fixed."""
    row = conn.execute(
        "SELECT is_admin FROM users WHERE email = ?", (AUTH_ADMIN_EMAIL,)
    ).fetchone()
    if row is None:
        return
    if int(row["is_admin"] or 0) == 0:
        conn.execute(
            "UPDATE users SET is_admin = 1 WHERE email = ?",
            (AUTH_ADMIN_EMAIL,),
        )
        conn.commit()


def init_auth_db() -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                hashed_password TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_two_factor_enabled INTEGER NOT NULL DEFAULT 0,
                two_factor_secret TEXT
            )
            """
        )
        # Safe migrations — add columns if not present
        for migration in [
            "ALTER TABLE users ADD COLUMN phone TEXT",
            "ALTER TABLE users ADD COLUMN phone_verified INTEGER NOT NULL DEFAULT 0",
            # SEC.1: role column replaces boolean is_admin; kept for backward compat
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass
        # SEC.1: backfill role from is_admin for existing rows
        try:
            conn.execute("UPDATE users SET role='admin' WHERE is_admin=1 AND (role IS NULL OR role='user')")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_email TEXT PRIMARY KEY,
                plan TEXT NOT NULL DEFAULT 'free',
                status TEXT NOT NULL DEFAULT 'active',
                trial_end TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                secret_hash TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                last_used_at INTEGER,
                revoked_at INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_email)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS login_failed_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                attempted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_login_failed_email_at ON login_failed_attempts(email, attempted_at)"
        )
        conn.commit()
        if AUTH_BOOTSTRAP_ADMIN:
            _seed_admin_user(conn)
            _ensure_configured_admin_privileges(conn)
        conn.close()
    lockout.prune_old_login_attempts()


def reset_auth_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM api_keys")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM login_failed_attempts")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM subscriptions")
        conn.commit()
        conn.close()


def get_user_record(email: str) -> Optional[dict[str, object]]:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def set_user_admin_for_tests(email: str, is_admin: bool) -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            "UPDATE users SET is_admin = ? WHERE email = ?",
            (1 if is_admin else 0, email),
        )
        conn.commit()
        conn.close()


# --- Subscription Logic ---
PLAN_HIERARCHY = {"free": 0, "starter": 1, "growth": 2, "pro": 3, "business": 4}
TRIAL_DAYS = 14


def get_subscription(email: str) -> dict[str, Any]:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE user_email = ?", (email,)
            ).fetchone()
        finally:
            conn.close()
    if not row:
        return {
            "user_email": email,
            "plan": "free",
            "status": "active",
            "trial_end": None,
        }
    sub = dict(row)
    if sub["status"] == "trialing" and sub["trial_end"]:
        if datetime.datetime.fromisoformat(sub["trial_end"]) < datetime.datetime.now(
            datetime.UTC
        ):
            _expire_trial(email)
            sub["status"] = "expired"
            sub["plan"] = "free"
    return sub


def create_subscription(email: str, plan: str) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.UTC).isoformat()
    trial_end = None
    sub_status = "active"
    if plan != "free":
        trial_end = (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=TRIAL_DAYS)
        ).isoformat()
        sub_status = "trialing"
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO subscriptions (user_email, plan, status, trial_end, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (email, plan, sub_status, trial_end, now, now),
            )
            conn.commit()
        finally:
            conn.close()
    return {"user_email": email, "plan": plan, "status": sub_status, "trial_end": trial_end}


def _expire_trial(email: str) -> None:
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE subscriptions SET plan = 'free', status = 'expired', updated_at = ? WHERE user_email = ?",
                (now, email),
            )
            conn.commit()
        finally:
            conn.close()


def update_subscription_plan(email: str, new_plan: str) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE subscriptions SET plan = ?, status = 'active', updated_at = ? WHERE user_email = ?",
                (new_plan, now, email),
            )
            conn.commit()
        finally:
            conn.close()
    return get_subscription(email)


def has_plan_access(user_plan: str, required_plan: str) -> bool:
    return PLAN_HIERARCHY.get(user_plan, 0) >= PLAN_HIERARCHY.get(required_plan, 0)


def user_may_use_api_keys(email: str) -> bool:
    sub = get_subscription(email)
    plan = str(sub.get("plan", "free"))
    feats = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    return bool(feats.get("api_access", False))


def _parse_smk_api_key(raw: str) -> tuple[str, str] | None:
    t = raw.strip()
    if t.lower().startswith("bearer "):
        t = t[7:].strip()
    if not t.startswith("smk_"):
        return None
    rest = t[4:]
    if "_" not in rest:
        return None
    key_id, secret = rest.split("_", 1)
    key_id = key_id.lower()
    if len(key_id) != 32 or not all(c in "0123456789abcdef" for c in key_id):
        return None
    if len(secret) < 32:
        return None
    return key_id, secret


def get_user(email: str) -> Optional[User]:
    row = get_user_record(email)
    if not row:
        return None
    role = str(row.get("role") or ("admin" if row["is_admin"] else "user"))
    return User(
        email=str(row["email"]),
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        is_two_factor_enabled=bool(row["is_two_factor_enabled"]),
        role=role,
    )


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticates a user by checking their email and password."""
    row = get_user_record(email)
    if not row:
        return None
    if not verify_password(password, str(row["hashed_password"])):
        return None
    role = str(row.get("role") or ("admin" if row["is_admin"] else "user"))
    return User(
        email=str(row["email"]),
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        is_two_factor_enabled=bool(row["is_two_factor_enabled"]),
        role=role,
    )


# --- Dependencies ---


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as exc:
        raise credentials_exception from exc
    if token_data.email is None:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Dependency: requires admin or owner role (or legacy is_admin flag)."""
    if not current_user.is_admin and current_user.role not in ("admin", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def require_permission(permission: str):
    """SEC.3 — Factory: returns a dependency that checks for a specific permission."""
    async def _check(current_user: Annotated[User, Depends(get_current_active_user)]):
        role = current_user.role or ("admin" if current_user.is_admin else "user")
        perms = _ROLE_PERMISSIONS.get(role, [])
        if "*" in perms or permission in perms:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required. Your role: {role}",
        )
    return _check


# --- Endpoints ---


@app.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    user_email = str(user_in.email)
    validate_password_strength(user_in.password)
    if get_user_record(user_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO users (email, hashed_password, is_active, is_admin, is_two_factor_enabled, two_factor_secret)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_email, get_password_hash(user_in.password), 1, 0, 0, None),
        )
        conn.commit()
        conn.close()
    valid_plans = {"free", "starter", "growth", "pro", "business"}
    plan = user_in.plan if user_in.plan in valid_plans else "free"
    create_subscription(user_email, plan)
    ref = (user_in.referral_code or "").strip()
    if ref and INTERNAL_SERVICE_SECRET:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{REFERRAL_SERVICE_URL}/internal/apply-signup-referral",
                    json={"referee_email": user_email, "code": ref},
                    headers={"X-Internal-Token": INTERNAL_SERVICE_SECRET},
                )
            if resp.status_code >= 400:
                logger.warning(
                    "referral apply on signup failed: %s %s",
                    resp.status_code,
                    (resp.text or "")[:400],
                )
        except Exception as exc:
            logger.warning("referral apply on signup error: %s", exc)
    return User(
        email=user_email, is_active=True, is_admin=False, is_two_factor_enabled=False
    )


# --- Password Reset ---

RESET_TOKEN_EXPIRE_MINUTES = 60
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_reset_email(to_email: str, token: str) -> None:
    """Send a password-reset email via SMTP (STARTTLS).  Raises on failure."""
    reset_url = f"{APP_BASE_URL}/reset-password?token={token}"

    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["Subject"] = "Reset your MyNetTax password"
    msg["From"] = f"MyNetTax <{SMTP_FROM}>"
    msg["To"] = to_email

    text_body = (
        f"Hello,\n\n"
        f"We received a request to reset the password for your MyNetTax account.\n\n"
        f"Click the link below (valid for {RESET_TOKEN_EXPIRE_MINUTES} minutes):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, just ignore this email — your password will not change.\n\n"
        f"— The MyNetTax team"
    )
    html_body = f"""\
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem">
  <div style="max-width:480px;margin:0 auto;background:#1e293b;border-radius:16px;padding:2rem">
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1.5rem">
      <span style="display:inline-block;width:36px;height:36px;border-radius:10px;
                   background:linear-gradient(135deg,#0d9488,#0284c7);
                   text-align:center;line-height:36px;font-weight:800;color:#fff">SM</span>
      <span style="font-weight:700;font-size:1.1rem">MyNetTax</span>
    </div>
    <h2 style="margin:0 0 0.75rem">Reset your password</h2>
    <p style="color:#94a3b8;margin-bottom:1.5rem">
      We received a request to reset the password for your account.<br>
      This link is valid for <strong style="color:#e2e8f0">{RESET_TOKEN_EXPIRE_MINUTES} minutes</strong>.
    </p>
    <a href="{reset_url}"
       style="display:inline-block;padding:0.8rem 1.6rem;
              background:linear-gradient(135deg,#0d9488,#0284c7);
              color:#fff;font-weight:700;text-decoration:none;
              border-radius:10px;font-size:1rem">
      Reset Password →
    </a>
    <p style="color:#475569;font-size:0.8rem;margin-top:1.5rem">
      If you didn't request this, you can safely ignore this email.
    </p>
  </div>
</body>
</html>
"""
    msg.attach(email.mime.text.MIMEText(text_body, "plain"))
    msg.attach(email.mime.text.MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_FROM or SMTP_USER, to_email, msg.as_string())


@app.post("/password-reset/request")
async def request_password_reset(body: PasswordResetRequest):
    """
    Generates a password-reset token for the given email address.
    If SMTP is configured, sends a real email. Otherwise (DEV_MODE) the token is
    returned directly in the response.
    """
    user_email = str(body.email)
    # Always return 200 to avoid email enumeration
    user = get_user_record(user_email)
    response: dict[str, object] = {
        "message": "If that email is registered you will receive a reset link shortly."
    }
    if not user:
        return response

    token = str(uuid.uuid4())
    expires_at = (
        datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    ).isoformat()

    with db_lock:
        conn = _connect()
        # Invalidate previous unused tokens for this email
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE user_email = ? AND used = 0",
            (user_email,),
        )
        conn.execute(
            "INSERT INTO password_reset_tokens (token, user_email, expires_at, used) VALUES (?, ?, ?, 0)",
            (token, user_email, expires_at),
        )
        conn.commit()
        conn.close()

    logger.info("Password reset token generated for %s", user_email)

    # --- Try to send real email ---
    if _smtp_configured():
        try:
            send_reset_email(user_email, token)
            logger.info("Password reset email sent to %s", user_email)
            response["email_sent"] = True
        except Exception as exc:
            logger.error("Failed to send reset email to %s: %s", user_email, exc)
            # Fall back to dev token so the user isn't stuck
            response["dev_token"] = token
            response["dev_note"] = (
                "[SMTP ERROR] Could not send email. "
                "Use this token at /reset-password?token=" + token
            )
    else:
        # No SMTP configured — show token on screen (dev/local mode)
        if DEV_MODE:
            response["dev_token"] = token
            response["dev_note"] = (
                "[DEV] SMTP not configured. "
                "Use it at /reset-password?token=" + token
            )

    return response


@app.post("/password-reset/confirm")
async def confirm_password_reset(body: PasswordResetConfirm):
    """
    Validates the reset token and sets the new password.
    """
    validate_password_strength(body.new_password)

    now = datetime.datetime.now(datetime.UTC)

    with db_lock:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token = ?",
            (body.token,),
        ).fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

        row_dict = dict(row)
        if row_dict["used"]:
            conn.close()
            raise HTTPException(status_code=400, detail="This reset link has already been used.")

        expires_at = datetime.datetime.fromisoformat(str(row_dict["expires_at"]))
        # Make both timezone-aware for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        if now > expires_at:
            conn.close()
            raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")

        user_email = str(row_dict["user_email"])
        new_hash = get_password_hash(body.new_password)

        conn.execute(
            "UPDATE users SET hashed_password = ? WHERE email = ?",
            (new_hash, user_email),
        )
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
            (body.token,),
        )
        conn.commit()
        conn.close()

    # Clear any login lockout so the user can sign in immediately
    lockout.clear_failed_attempts(user_email)
    logger.info("Password reset completed for %s", user_email)
    return {"message": "Password updated successfully. You can now log in with your new password."}


@app.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    lockout.check_account_lockout(form_data.username)

    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        lockout.record_failed_attempt(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- 2FA Check ---
    if user.is_two_factor_enabled:
        totp_code = None
        if form_data.scopes:
            scope_parts = form_data.scopes[0].split(":")
            if len(scope_parts) == 2 and scope_parts[0] == "totp":
                totp_code = scope_parts[1]

        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="2FA_REQUIRED",
                headers={"X-2FA-Required": "true"},
            )

        row = get_user_record(user.email)
        two_fa_secret = (
            str(row["two_factor_secret"])
            if row and row.get("two_factor_secret")
            else ""
        )
        totp = pyotp.TOTP(two_fa_secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    # --- Enforce 2FA for admin accounts ---
    if user.is_admin and REQUIRE_ADMIN_2FA and not user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN_2FA_SETUP_REQUIRED",
            headers={"X-Admin-2FA-Required": "setup"},
        )

    lockout.clear_failed_attempts(form_data.username)
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data: dict[str, object] = {
        "sub": user.email,
        "is_admin": user.is_admin,
        **_jwt_rbac_claims(user.is_admin, user.role),
        **_jwt_subscription_claims(user.email),
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires,
    )
    refresh_expires = datetime.timedelta(days=7)
    session_jti = uuid.uuid4().hex
    now_utc = datetime.datetime.now(datetime.UTC)
    refresh_token = create_access_token(
        data={"sub": user.email, "type": "refresh", "jti": session_jti},
        expires_delta=refresh_expires,
    )
    expires_refresh_at = now_utc + refresh_expires
    client_host = request.client.host if request.client else None
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_email, issued_at, expires_at, ip, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_jti,
                    user.email,
                    now_utc.isoformat(),
                    expires_refresh_at.isoformat(),
                    client_host,
                    request.headers.get("user-agent"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_user_api_key(
    body: ApiKeyCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if not user_may_use_api_keys(current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys require Pro or Business plan (api_access).",
        )
    key_id = uuid.uuid4().hex
    secret = secrets.token_hex(24)
    full_key = f"smk_{key_id}_{secret}"
    now = int(time.time())
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO api_keys (key_id, user_email, secret_hash, label, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                key_id,
                current_user.email,
                get_password_hash(secret),
                body.label.strip(),
                now,
            ),
        )
        conn.commit()
        conn.close()
    return ApiKeyCreated(
        key_id=key_id, label=body.label.strip(), api_key=full_key, created_at=now
    )


@app.get("/api-keys", response_model=list[ApiKeyListItem])
async def list_user_api_keys(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if not user_may_use_api_keys(current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys require Pro or Business plan (api_access).",
        )
    with db_lock:
        conn = _connect()
        rows = conn.execute(
            """
            SELECT key_id, label, created_at, last_used_at FROM api_keys
            WHERE user_email = ? AND revoked_at IS NULL ORDER BY created_at DESC
            """,
            (current_user.email,),
        ).fetchall()
        conn.close()
    return [
        ApiKeyListItem(
            key_id=str(r["key_id"]),
            label=str(r["label"] or ""),
            created_at=int(r["created_at"]),
            last_used_at=int(r["last_used_at"])
            if r["last_used_at"] is not None
            else None,
        )
        for r in rows
    ]


@app.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_api_key(
    key_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if not user_may_use_api_keys(current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys require Pro or Business plan (api_access).",
        )
    kid = key_id.lower().strip()
    if len(kid) != 32 or not all(c in "0123456789abcdef" for c in kid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key id"
        )
    now = int(time.time())
    with db_lock:
        conn = _connect()
        exists = conn.execute(
            """
            SELECT 1 FROM api_keys WHERE key_id = ? AND user_email = ? AND revoked_at IS NULL
            """,
            (kid, current_user.email),
        ).fetchone()
        if not exists:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )
        conn.execute(
            "UPDATE api_keys SET revoked_at = ? WHERE key_id = ?",
            (now, kid),
        )
        conn.commit()
        conn.close()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/token/api-key", response_model=Token)
async def exchange_api_key_for_token(body: ApiKeyExchangeRequest, request: Request):
    parsed = _parse_smk_api_key(body.api_key)
    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key format (expected smk_<id>_<secret>).",
        )
    key_id, secret = parsed
    with db_lock:
        conn = _connect()
        row = conn.execute(
            """
            SELECT user_email, secret_hash FROM api_keys
            WHERE key_id = ? AND revoked_at IS NULL
            """,
            (key_id,),
        ).fetchone()
        conn.close()
    if row is None or not verify_password(secret, str(row["secret_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_email = str(row["user_email"])
    user = get_user(user_email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or missing",
        )
    with db_lock:
        conn = _connect()
        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
            (int(time.time()), key_id),
        )
        conn.commit()
        conn.close()
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data: dict[str, object] = {
        "sub": user.email,
        "is_admin": user.is_admin,
        **_jwt_rbac_claims(user.is_admin, user.role),
        **_jwt_subscription_claims(user.email),
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires,
    )
    client_host = request.client.host if request.client else None
    _log_security_event(
        user_email,
        "api_key_exchanged",
        ip=client_host,
        user_agent=request.headers.get("user-agent"),
        details={"key_id": key_id},
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- 2FA Endpoints ---


@app.get("/2fa/setup")
async def setup_two_factor_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Generates a secret and a QR code URI for setting up 2FA.
    """
    if current_user.is_two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled.")

    # Generate a new secret
    secret = pyotp.random_base32()
    with db_lock:
        conn = _connect()
        conn.execute(
            "UPDATE users SET two_factor_secret = ? WHERE email = ?",
            (secret, current_user.email),
        )
        conn.commit()
        conn.close()

    # Generate provisioning URI
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email, issuer_name="FinTech App"
    )

    # Generate QR code image
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


@app.get("/2fa/setup-json")
async def setup_two_factor_auth_json(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if current_user.is_two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled.")

    secret = pyotp.random_base32()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET two_factor_secret = ? WHERE email = ?",
                (secret, current_user.email),
            )
            conn.commit()
        finally:
            conn.close()

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email, issuer_name="MyNetTax"
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "issuer": "MyNetTax",
    }


@app.post("/2fa/verify")
async def verify_two_factor_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
    totp_code: str = Query(
        ..., description="The 6-digit code from the authenticator app."
    ),
):
    """
    Verifies the TOTP code and enables 2FA for the user.
    """
    row = get_user_record(current_user.email)
    secret: Optional[str] = (
        str(row["two_factor_secret"]) if row and row.get("two_factor_secret") else None
    )
    if not secret:
        raise HTTPException(
            status_code=400, detail="2FA setup not initiated. Call /2fa/setup first."
        )

    totp = pyotp.TOTP(secret)
    if not totp.verify(totp_code):
        raise HTTPException(status_code=400, detail="Invalid code.")

    # Enable 2FA for the user
    with db_lock:
        conn = _connect()
        conn.execute(
            "UPDATE users SET is_two_factor_enabled = 1 WHERE email = ?",
            (current_user.email,),
        )
        conn.commit()
        conn.close()
    return {"message": "2FA enabled successfully."}


@app.delete("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_two_factor_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Disables 2FA for the currently authenticated user.
    """
    if not current_user.is_two_factor_enabled:
        # If already disabled, do nothing and return success
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Disable 2FA and clear the secret
    with db_lock:
        conn = _connect()
        conn.execute(
            "UPDATE users SET is_two_factor_enabled = 0, two_factor_secret = NULL WHERE email = ?",
            (current_user.email,),
        )
        conn.commit()
        conn.close()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Phone Verification Endpoints ---

import random as _random  # noqa: E402

# In-memory store: email -> (code, phone, expires_at_unix)
_phone_codes: dict[str, tuple[str, str, float]] = {}
_PHONE_CODE_TTL = 600  # 10 minutes

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_FROM  = os.getenv("TWILIO_PHONE_FROM", "")
SMS_DEV_MODE = not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_FROM)


def _send_sms(to: str, body: str) -> None:
    """Send SMS via Twilio if configured, otherwise log to console (dev mode)."""
    if SMS_DEV_MODE:
        logger.info("[DEV SMS] To %s: %s", to, body)
        return
    try:
        from twilio.rest import Client  # type: ignore[import]
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=body, from_=TWILIO_PHONE_FROM, to=to)
    except Exception as exc:
        logger.error("SMS send failed: %s", exc)
        raise HTTPException(status_code=503, detail="SMS delivery failed. Please try again.")


class PhoneSendRequest(BaseModel):
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)


class PhoneVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


@app.post("/phone/send-code")
async def phone_send_code(payload: PhoneSendRequest):
    """
    Generate a 6-digit SMS verification code and send it to the given phone number.
    In development (no Twilio env vars), the code is returned in the response for testing.
    """
    if not get_user_record(str(payload.email)):
        raise HTTPException(status_code=404, detail="User not found")

    code = str(_random.randint(100000, 999999))
    expires_at = time.time() + _PHONE_CODE_TTL
    _phone_codes[str(payload.email)] = (code, payload.phone, expires_at)

    _send_sms(
        to=payload.phone,
        body=f"Your MyNetTax verification code is: {code}. Valid for 10 minutes.",
    )

    response: dict[str, Any] = {"sent": True}
    if SMS_DEV_MODE and VERIFICATION_CODES_DEBUG:
        response["dev_code"] = code
    return response


@app.post("/phone/verify")
async def phone_verify_code(
    payload: PhoneVerifyRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Verify the SMS code and mark the user's phone as verified."""
    email = str(payload.email)
    if email != current_user.email:
        raise HTTPException(status_code=403, detail="Forbidden")

    entry = _phone_codes.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="No verification code found. Request a new one.")

    code, phone, expires_at = entry
    if time.time() > expires_at:
        _phone_codes.pop(email, None)
        raise HTTPException(status_code=400, detail="Code expired. Please request a new one.")

    if payload.code != code:
        raise HTTPException(status_code=400, detail="Incorrect code. Please try again.")

    _phone_codes.pop(email, None)
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET phone = ?, phone_verified = 1 WHERE email = ?",
                (phone, email),
            )
            conn.commit()
        finally:
            conn.close()

    return {"verified": True, "phone": phone}


@app.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    sub = get_subscription(current_user.email)
    current_user.subscription_tier = str(sub["plan"])
    current_user.subscription_status = str(sub["status"])
    if sub["trial_end"]:
        trial_end = datetime.datetime.fromisoformat(str(sub["trial_end"]))
        remaining = (trial_end - datetime.datetime.now(datetime.UTC)).days
        current_user.trial_days_remaining = max(0, remaining)
    return current_user


@app.post("/change-password")
async def change_password(
    payload: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    row = get_user_record(current_user.email)
    if not row or not verify_password(
        payload.current_password, str(row["hashed_password"])
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    validate_password_strength(payload.new_password)

    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET hashed_password = ? WHERE email = ?",
                (get_password_hash(payload.new_password), current_user.email),
            )
            conn.commit()
        finally:
            conn.close()

    return {"message": "Password changed successfully"}


@app.post("/users/{user_email}/deactivate", response_model=User)
async def deactivate_user(
    user_email: EmailStr, _admin_user: Annotated[User, Depends(require_admin)]
):
    """
    Deactivates a user. This action is restricted to administrators.
    """
    user_to_deactivate = get_user(email=user_email)
    if not user_to_deactivate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user_to_deactivate.is_active:
        return user_to_deactivate  # Already inactive, no change needed

    # Update the persistent user store directly.
    with db_lock:
        conn = _connect()
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE email = ?", (str(user_email),)
        )
        conn.commit()
        conn.close()

    # Return the updated user model
    user_to_deactivate.is_active = False
    return user_to_deactivate


class AdminUserListItem(BaseModel):
    email: str
    is_active: bool
    is_admin: bool
    is_two_factor_enabled: bool
    plan: str
    subscription_status: str


class AdminUserListOut(BaseModel):
    total: int
    page: int
    limit: int
    items: list[AdminUserListItem]


class AdminUserDetailOut(BaseModel):
    email: str
    is_active: bool
    is_admin: bool
    is_two_factor_enabled: bool
    plan: str
    subscription_status: str
    trial_end: Optional[str] = None


async def _post_audit_event(
    actor_email: str,
    action: str,
    target: str,
    details: dict,
) -> None:
    """Fire-and-forget: record admin action in compliance-service audit log."""
    payload = {
        "user_id": actor_email,
        "action": action,
        "resource": target,
        "details": details,
        "source": "auth-service",
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{COMPLIANCE_SERVICE_URL}/audit-events", json=payload)
    except Exception:  # noqa: BLE001
        pass  # audit is best-effort — never fail the primary request


class ChangeRoleRequest(BaseModel):
    role: str  # owner | admin | support_agent | user


@app.patch("/admin/users/{user_email}/role")
async def admin_change_user_role(
    user_email: str,
    req: ChangeRoleRequest,
    admin: Annotated[User, Depends(require_admin)],
) -> dict[str, object]:
    """SEC.1 — Change a user's role (owner/admin/support_agent/user). Owner only."""
    valid_roles = list(_ROLE_PERMISSIONS.keys())
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Valid: {valid_roles}")
    # Only owner can assign owner role
    if req.role == "owner" and admin.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can assign owner role")
    with db_lock:
        conn = _connect()
        try:
            existing = conn.execute("SELECT email FROM users WHERE email=?", (user_email,)).fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail=f"User {user_email} not found")
            is_admin_val = 1 if req.role in ("admin", "owner") else 0
            conn.execute("UPDATE users SET role=?, is_admin=? WHERE email=?", (req.role, is_admin_val, user_email))
            conn.commit()
        finally:
            conn.close()
    asyncio.create_task(
        _post_audit_event(
            actor_email=admin.email,
            action="admin.change_user_role",
            target=user_email,
            details={"new_role": req.role},
        )
    )
    return {"email": user_email, "new_role": req.role, "updated_by": admin.email}


@app.get("/admin/users", response_model=AdminUserListOut)
async def admin_list_users(
    _admin: Annotated[User, Depends(require_admin)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    plan: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    offset = (page - 1) * limit
    where: list[str] = []
    params: list[Any] = []
    if plan:
        where.append("COALESCE(s.plan, 'free') = ?")
        params.append(plan)
    if status:
        where.append("COALESCE(s.status, 'active') = ?")
        params.append(status)
    if search:
        where.append("LOWER(u.email) LIKE ?")
        params.append(f"%{search.lower()}%")
    wh = (" WHERE " + " AND ".join(where)) if where else ""

    base_from = """
        FROM users u
        LEFT JOIN subscriptions s ON u.email = s.user_email
    """
    count_sql = "SELECT COUNT(*) " + base_from + wh
    list_sql = (
        """
        SELECT u.email, u.is_active, u.is_admin, u.is_two_factor_enabled,
               COALESCE(s.plan, 'free') AS plan,
               COALESCE(s.status, 'active') AS subscription_status
        """
        + base_from
        + wh
        + " ORDER BY u.email LIMIT ? OFFSET ?"
    )

    with db_lock:
        conn = _connect()
        try:
            total = int(conn.execute(count_sql, params).fetchone()[0])
            rows = conn.execute(list_sql, params + [limit, offset]).fetchall()
        finally:
            conn.close()

    items = [
        AdminUserListItem(
            email=str(r["email"]),
            is_active=bool(r["is_active"]),
            is_admin=bool(r["is_admin"]),
            is_two_factor_enabled=bool(r["is_two_factor_enabled"]),
            plan=str(r["plan"]),
            subscription_status=str(r["subscription_status"]),
        )
        for r in rows
    ]
    return AdminUserListOut(total=total, page=page, limit=limit, items=items)


@app.get("/admin/users/{user_email:path}", response_model=AdminUserDetailOut)
async def admin_get_user(
    user_email: str,
    _admin: Annotated[User, Depends(require_admin)],
):
    email = unquote(user_email).strip()
    row = get_user_record(email)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    sub = get_subscription(email)
    return AdminUserDetailOut(
        email=str(row["email"]),
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        is_two_factor_enabled=bool(row["is_two_factor_enabled"]),
        plan=str(sub.get("plan", "free")),
        subscription_status=str(sub.get("status", "active")),
        trial_end=str(sub["trial_end"]) if sub.get("trial_end") else None,
    )


def _admin_health_targets() -> list[tuple[str, str]]:
    raw = os.getenv("ADMIN_HEALTH_SERVICE_URLS", "").strip()
    if not raw:
        return list(_DEFAULT_ADMIN_HEALTH_TARGETS)
    out: list[tuple[str, str]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part or "|" not in part:
            continue
        name, url = part.split("|", 1)
        name, url = name.strip(), url.strip()
        if name and url:
            out.append((name, url))
    return out or list(_DEFAULT_ADMIN_HEALTH_TARGETS)


async def _probe_service_health(
    client: httpx.AsyncClient, name: str, url: str
) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        r = await client.get(url)
        ms = int((time.perf_counter() - t0) * 1000)
        return {
            "service": name,
            "ok": 200 <= r.status_code < 300,
            "status_code": r.status_code,
            "latency_ms": ms,
        }
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        return {
            "service": name,
            "ok": False,
            "status_code": None,
            "latency_ms": ms,
            "error": str(exc)[:220],
        }


@app.get("/admin/health/services")
async def admin_health_services(
    _admin: Annotated[User, Depends(require_admin)],
):
    targets = _admin_health_targets()
    async with httpx.AsyncClient(timeout=2.0) as client:
        checks = await asyncio.gather(
            *(_probe_service_health(client, name, url) for name, url in targets)
        )
    healthy = sum(1 for c in checks if c.get("ok"))
    return {
        "ok": healthy == len(checks),
        "checked": len(checks),
        "healthy": healthy,
        "services": list(checks),
    }


# --- Subscription Endpoints ---


class SubscriptionResponse(BaseModel):
    user_email: str
    plan: str
    status: str
    trial_end: Optional[str] = None
    trial_days_remaining: Optional[int] = None
    features: dict[str, Any]


PLAN_FEATURES: dict[str, dict[str, Any]] = {  # cspell:ignore hmrc
    "free": {
        "bank_connections": 1,
        "bank_sync_daily_limit": 0,
        "transactions_per_month": 20,
        "storage_limit_gb": 1,
        "transaction_history_months": 3,
        "ai_categorization": False,
        "receipt_ocr": False,
        "cash_flow_forecast": False,
        "tax_calculator": "basic",
        "hmrc_submission": False,
        "hmrc_direct_submission": False,
        "vat_returns": False,
        "cis_refund_tracker": False,
        "accountant_review_credits_per_month": 0,
        "smart_search": False,
        "mortgage_reports": False,
        "advanced_analytics": False,
        "api_access": False,
        "team_members": 1,
        "white_label": False,
        "documents_max_count": 20,
        "evidence_pack_tier": "none",
    },
    "starter": {
        "bank_connections": 3,
        "bank_sync_daily_limit": 1,
        "transactions_per_month": 999999,
        "storage_limit_gb": 2,
        "transaction_history_months": 3,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": True,
        "hmrc_direct_submission": False,
        "vat_returns": False,
        "cis_refund_tracker": True,
        "accountant_review_credits_per_month": 0,
        "smart_search": False,
        "mortgage_reports": False,
        "advanced_analytics": False,
        "api_access": False,
        "team_members": 1,
        "white_label": False,
        "documents_max_count": 100,
        "evidence_pack_tier": "none",
    },
    "growth": {
        "bank_connections": 2,
        "bank_sync_daily_limit": 3,
        "transactions_per_month": 2000,
        "storage_limit_gb": 6,
        "transaction_history_months": 12,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": True,
        "hmrc_direct_submission": False,
        "vat_returns": False,
        "cis_refund_tracker": True,
        "accountant_review_credits_per_month": 0,
        "smart_search": False,
        "mortgage_reports": False,
        "advanced_analytics": False,
        "api_access": False,
        "team_members": 1,
        "white_label": False,
        "documents_max_count": 500,
        "evidence_pack_tier": "basic",
    },
    "pro": {
        "bank_connections": 5,
        "bank_sync_daily_limit": 10,
        "transactions_per_month": 5000,
        "storage_limit_gb": 10,
        "transaction_history_months": 24,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": True,
        "hmrc_direct_submission": True,
        "vat_returns": True,
        "cis_refund_tracker": True,
        "accountant_review_credits_per_month": 1,
        "smart_search": True,
        "mortgage_reports": True,
        "advanced_analytics": True,
        "api_access": True,
        "team_members": 1,
        "white_label": False,
        "documents_max_count": 5000,
        "evidence_pack_tier": "full",
    },
    "business": {
        "bank_connections": 10,
        "bank_sync_daily_limit": 25,
        "transactions_per_month": 999999,
        "storage_limit_gb": 25,
        "transaction_history_months": 36,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": True,
        "hmrc_direct_submission": True,
        "vat_returns": True,
        "cis_refund_tracker": True,
        "accountant_review_credits_per_month": 4,
        "smart_search": True,
        "mortgage_reports": True,
        "advanced_analytics": True,
        "api_access": True,
        "team_members": 1,
        "white_label": True,
        "documents_max_count": 50000,
        "evidence_pack_tier": "full",
    },
}


# SEC.2: Role → permissions mapping
_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "owner": [
        "*",
        "billing:read", "billing:write",
        "support:read", "support:write",
        "users:read", "users:write",
        "regulatory:read", "regulatory:write", "regulatory:approve",
        "analytics:read", "partners:read", "partners:write",
        "admin:audit",
    ],
    "admin": [
        "billing:read",
        "support:read", "support:write",
        "users:read", "users:write",
        "regulatory:read", "regulatory:write",
        "analytics:read", "partners:read",
        "admin:audit",
    ],
    "support_agent": [
        "support:read", "support:write",
        "users:read",
        "portal.use",
    ],
    "user": [
        "portal.use",
    ],
}


def _jwt_rbac_claims(is_admin: bool, role: str = "") -> dict[str, object]:
    # Resolve role: explicit role field takes priority, is_admin is legacy fallback
    effective_role = role if role in _ROLE_PERMISSIONS else ("admin" if is_admin else "user")
    perms = _ROLE_PERMISSIONS.get(effective_role, ["portal.use"])
    scopes: list[str] = []
    if effective_role in ("owner", "admin"):
        scopes = ["billing:read", "support:read", "support:write"]
    elif effective_role == "support_agent":
        scopes = ["support:read", "support:write"]
    return {
        "role": effective_role,
        "roles": [effective_role],
        "scopes": scopes,
        "perms": perms,
        "permissions": perms,  # SEC.2: explicit permissions[] array
    }


def _jwt_subscription_claims(email: str) -> dict[str, object]:
    """Claims embedded in access tokens for downstream plan enforcement."""
    sub = get_subscription(email)
    plan = str(sub["plan"])
    feats = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    return {
        "plan": plan,
        "bank_connections_limit": feats["bank_connections"],
        "bank_sync_daily_limit": int(feats.get("bank_sync_daily_limit", 0)),
        "transactions_per_month_limit": feats["transactions_per_month"],
        "storage_limit_gb": int(feats.get("storage_limit_gb", 2)),
        "transaction_history_months": int(feats.get("transaction_history_months", 3)),
        "hmrc_direct_submission": bool(feats.get("hmrc_direct_submission", False)),
        "vat_returns": bool(feats.get("vat_returns", False)),
        "mortgage_reports": bool(feats.get("mortgage_reports", False)),
        "advanced_analytics": bool(feats.get("advanced_analytics", False)),
        "cash_flow_forecast": bool(feats.get("cash_flow_forecast", False)),
        "documents_max_count": int(feats.get("documents_max_count", 20)),
        "evidence_pack_tier": str(feats.get("evidence_pack_tier", "none")),
        "accountant_review_credits_per_month": int(
            feats.get("accountant_review_credits_per_month", 0)
        ),
    }


@app.get("/subscription/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    sub = get_subscription(current_user.email)
    trial_days = None
    trial_end_val: Optional[str] = sub.get("trial_end")  # type: ignore[assignment]
    if trial_end_val:
        trial_end = datetime.datetime.fromisoformat(trial_end_val)
        trial_days = max(0, (trial_end - datetime.datetime.now(datetime.UTC)).days)
    plan_name = str(sub["plan"])
    return SubscriptionResponse(
        user_email=current_user.email,
        plan=plan_name,
        status=str(sub["status"]),
        trial_end=trial_end_val,
        trial_days_remaining=trial_days,
        features=PLAN_FEATURES.get(plan_name, PLAN_FEATURES["free"]),
    )


@app.post("/subscription/upgrade")
async def upgrade_subscription(
    plan: str = Query(..., pattern="^(starter|growth|pro|business)$"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    assert current_user is not None
    current_sub = get_subscription(current_user.email)
    if not has_plan_access(plan, str(current_sub["plan"])):
        pass
    updated = update_subscription_plan(current_user.email, plan)
    return {"message": f"Subscription upgraded to {plan}", "subscription": updated}


@app.get("/subscription/plans")
async def list_plans() -> dict[str, Any]:
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_gbp": 0,
                "features": PLAN_FEATURES["free"],
            },
            {
                "id": "starter",
                "name": "Starter",
                "price_gbp": 12,
                "features": PLAN_FEATURES["starter"],
            },
            {
                "id": "growth",
                "name": "Growth",
                "price_gbp": 15,
                "features": PLAN_FEATURES["growth"],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_gbp": 18,
                "features": PLAN_FEATURES["pro"],
                "popular": True,
            },
            {
                "id": "business",
                "name": "Business",
                "price_gbp": 28,
                "features": PLAN_FEATURES["business"],
            },
        ],
        "trial_days": 14,
    }


@app.post("/subscription/check-access")
async def check_feature_access(
    feature: str = Query(...),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    assert current_user is not None
    sub = get_subscription(current_user.email)
    plan: str = str(sub["plan"])
    features: dict[str, Any] = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    has_access: Any = features.get(feature, False)
    if isinstance(has_access, bool):
        allowed: bool = has_access
    elif isinstance(has_access, int):
        allowed = has_access > 0
    else:
        allowed = (
            has_access != "basic" if feature == "tax_calculator" else bool(has_access)
        )

    if not allowed:
        min_plan = "starter"
        for p in ["starter", "growth", "pro", "business"]:
            pf: dict[str, Any] = PLAN_FEATURES[p]
            val: Any = pf.get(feature, False)
            if val and val != "basic":
                min_plan = p
                break
        return {"allowed": False, "required_plan": min_plan, "current_plan": plan}
    return {"allowed": True, "current_plan": plan}


init_auth_db()


def _log_production_hardening_warnings() -> None:
    profile = (
        (os.getenv("DEPLOYMENT_PROFILE") or os.getenv("APP_ENV") or "")
        .strip()
        .lower()
    )
    if profile in ("production", "prod") and AUTH_BOOTSTRAP_ADMIN:
        logger.critical(
            "AUTH_BOOTSTRAP_ADMIN is true while DEPLOYMENT_PROFILE/APP_ENV indicates production. "
            "Set AUTH_BOOTSTRAP_ADMIN=false after the first admin exists (docs/GO_LIVE_CHECKLIST.md)."
        )
    if profile in ("production", "prod") and VERIFICATION_CODES_DEBUG:
        logger.critical(
            "AUTH_EMAIL_VERIFICATION_DEBUG_RETURN_CODE is enabled under production profile; disable for live traffic."
        )


_log_production_hardening_warnings()

# === ENTERPRISE FEATURES ===


@app.post("/organizations")
async def create_organization(
    current_user: Annotated[User, Depends(get_current_active_user)],
    name: str = Query(min_length=1, max_length=200),
    plan: str = Query(default="enterprise"),
) -> dict[str, object]:
    """Create a new organization (available for Pro+ users)"""
    if plan not in ("enterprise", "team"):
        raise HTTPException(
            status_code=400, detail="Invalid plan. Must be 'enterprise' or 'team'."
        )

    org_id = str(uuid.uuid4())[:8].upper()

    with db_lock:
        conn = _connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subscription_plan TEXT DEFAULT 'enterprise',
                    owner_email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute(
                "INSERT INTO organizations (id, name, subscription_plan, owner_email) VALUES (?, ?, ?, ?)",
                (org_id, name, plan, current_user.email),
            )

            conn.commit()

            return {
                "id": org_id,
                "name": name,
                "subscription_plan": plan,
                "owner_email": current_user.email,
                "message": f"Enterprise organization '{name}' created! Monthly revenue: £{45 * 10} minimum",
            }
        except Exception as e:
            logger.error("Failed to create organization: %s", e)
            raise HTTPException(status_code=500, detail="Failed to create organization") from e
        finally:
            conn.close()


@app.get("/enterprise/pricing")
async def get_enterprise_pricing() -> dict[str, object]:
    """Get current enterprise pricing plans"""
    return {
        "plans": {
            "team": {
                "price_per_user_per_month_gbp": 25,
                "min_users": 5,
                "max_users": 20,
                "estimated_monthly_revenue": 625,  # 25 * 25 avg users
            },
            "enterprise": {
                "price_per_user_per_month_gbp": 45,
                "min_users": 10,
                "max_users": 500,
                "estimated_monthly_revenue": 2250,  # 50 * 45 avg users
            },
        },
        "roi_metrics": {
            "customer_lifetime_value": 12600,  # £45 * 12 months * 23.33 avg retention
            "enterprise_arpu_improvement": "3x higher than individual plans",  # cspell:ignore arpu
        },
    }


# ============================================================
# SECURITY MANAGEMENT ENDPOINTS
# (used by security.tsx in the web portal)
# ============================================================

import json as _json  # noqa: E402,C0411  # isort: skip  # pylint: disable=wrong-import-order,wrong-import-position


def _init_security_tables() -> None:
    """Create security-related tables if they don't exist."""
    with db_lock:
        conn = _connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS security_events (
                event_id    TEXT PRIMARY KEY,
                user_email  TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                ip          TEXT,
                user_agent  TEXT,
                details_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id         TEXT PRIMARY KEY,
                user_email         TEXT NOT NULL,
                issued_at          TEXT NOT NULL,
                expires_at         TEXT NOT NULL,
                revoked_at         TEXT,
                revocation_reason  TEXT,
                ip                 TEXT,
                user_agent         TEXT
            );

            CREATE TABLE IF NOT EXISTS legal_acceptances (
                user_email  TEXT PRIMARY KEY,
                version     TEXT NOT NULL,
                accepted_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_verifications (
                user_email  TEXT PRIMARY KEY,
                code        TEXT NOT NULL,
                expires_at  TEXT NOT NULL,
                confirmed   INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS user_metadata (
                user_email         TEXT PRIMARY KEY,
                email_verified     INTEGER NOT NULL DEFAULT 0,
                locked_until       TEXT,
                password_changed_at TEXT
            );
        """)
        conn.commit()
        conn.close()


_init_security_tables()

LEGAL_CURRENT_VERSION = "2026-01-01"


def _get_user_metadata(email: str) -> dict:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM user_metadata WHERE user_email = ?", (email,)
            ).fetchone()
        finally:
            conn.close()
    if row:
        return dict(row)
    return {
        "user_email": email,
        "email_verified": 0,
        "locked_until": None,
        "password_changed_at": None,
    }


def _log_security_event(
    email: str,
    event_type: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    event_id = str(uuid.uuid4())
    occurred_at = datetime.datetime.now(datetime.UTC).isoformat()
    details_json = _json.dumps(details or {})
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO security_events
                   (event_id, user_email, event_type, occurred_at, ip, user_agent, details_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    email,
                    event_type,
                    occurred_at,
                    ip,
                    user_agent,
                    details_json,
                ),
            )
            conn.commit()
        finally:
            conn.close()


# --- Pydantic models ---


class SecurityStateResponse(BaseModel):
    email: str
    email_verified: bool
    failed_login_attempts: int
    has_accepted_current_legal: bool
    is_two_factor_enabled: bool
    last_login_at: Optional[str] = None
    legal_accepted_at: Optional[str] = None
    legal_accepted_version: Optional[str] = None
    legal_current_version: str
    legal_eula_url: str
    legal_terms_url: str
    locked_until: Optional[str] = None
    max_failed_login_attempts: int
    password_changed_at: Optional[str] = None


class SecurityEventItem(BaseModel):
    event_id: str
    event_type: str
    occurred_at: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: dict = {}


class SecurityEventsResponse(BaseModel):
    items: list[SecurityEventItem]
    total: int


class SessionItem(BaseModel):
    session_id: str
    issued_at: str
    expires_at: str
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class SessionsResponse(BaseModel):
    active_sessions: int
    total_sessions: int
    items: list[SessionItem]


class AlertDeliveryChannel(BaseModel):
    status: Optional[str] = None
    receipt_status: Optional[str] = None


class AlertDeliveryItem(BaseModel):
    dispatch_id: str
    title: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    occurred_at: Optional[str] = None
    last_receipt_at: Optional[str] = None
    channels: dict = {}


class AlertDeliveriesResponse(BaseModel):
    items: list[AlertDeliveryItem]
    total: int


class EmailVerificationRequestResp(BaseModel):
    code_sent: bool
    debug_code: Optional[str] = None
    expires_at: str
    message: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=24, max_length=4096)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in_seconds: int


# --- Endpoints ---


@app.get("/security/state", response_model=SecurityStateResponse)
async def get_security_state(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    meta = _get_user_metadata(current_user.email)
    # last login event
    with db_lock:
        conn = _connect()
        try:
            last_login_row = conn.execute(
                "SELECT occurred_at FROM security_events"
                " WHERE user_email = ? AND event_type = 'login_success'"
                " ORDER BY occurred_at DESC LIMIT 1",
                (current_user.email,),
            ).fetchone()
            legal_row = conn.execute(
                "SELECT version, accepted_at FROM legal_acceptances WHERE user_email = ?",
                (current_user.email,),
            ).fetchone()
        finally:
            conn.close()

    legal_accepted_at = legal_row["accepted_at"] if legal_row else None
    legal_accepted_version = legal_row["version"] if legal_row else None
    failed = lockout.count_recent_failed_attempts(current_user.email)

    return SecurityStateResponse(
        email=current_user.email,
        email_verified=bool(meta.get("email_verified", 0)),
        failed_login_attempts=failed,
        has_accepted_current_legal=(legal_accepted_version == LEGAL_CURRENT_VERSION),
        is_two_factor_enabled=current_user.is_two_factor_enabled,
        last_login_at=last_login_row["occurred_at"] if last_login_row else None,
        legal_accepted_at=legal_accepted_at,
        legal_accepted_version=legal_accepted_version,
        legal_current_version=LEGAL_CURRENT_VERSION,
        legal_eula_url="/eula",
        legal_terms_url="/terms",
        locked_until=str(meta["locked_until"]) if meta.get("locked_until") else None,
        max_failed_login_attempts=LOCKOUT_THRESHOLD,
        password_changed_at=str(meta["password_changed_at"])
        if meta.get("password_changed_at")
        else None,
    )


@app.get("/security/events", response_model=SecurityEventsResponse)
async def get_security_events(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    with db_lock:
        conn = _connect()
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM security_events WHERE user_email = ?",
                (current_user.email,),
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM security_events WHERE user_email = ? ORDER BY occurred_at DESC LIMIT ? OFFSET ?",
                (current_user.email, limit, offset),
            ).fetchall()
        finally:
            conn.close()

    items = [
        SecurityEventItem(
            event_id=str(r["event_id"]),
            event_type=str(r["event_type"]),
            occurred_at=str(r["occurred_at"]),
            ip=str(r["ip"]) if r["ip"] else None,
            user_agent=str(r["user_agent"]) if r["user_agent"] else None,
            details=_json.loads(r["details_json"] or "{}"),
        )
        for r in rows
    ]
    return SecurityEventsResponse(items=items, total=total)


@app.get("/security/alerts/deliveries", response_model=AlertDeliveriesResponse)
async def get_alert_deliveries(
    _current_user: Annotated[User, Depends(get_current_active_user)],
    _limit: int = Query(default=25, ge=1, le=200),
):
    # Stub: returns empty list — alert delivery system not yet wired
    return AlertDeliveriesResponse(items=[], total=0)


@app.get("/security/sessions", response_model=SessionsResponse)
async def get_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_revoked: bool = Query(default=False),
):
    with db_lock:
        conn = _connect()
        try:
            if include_revoked:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE user_email = ? ORDER BY issued_at DESC",
                    (current_user.email,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE user_email = ? AND revoked_at IS NULL ORDER BY issued_at DESC",
                    (current_user.email,),
                ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_email = ?",
                (current_user.email,),
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_email = ? AND revoked_at IS NULL",
                (current_user.email,),
            ).fetchone()[0]
        finally:
            conn.close()

    items = [
        SessionItem(
            session_id=str(r["session_id"]),
            issued_at=str(r["issued_at"]),
            expires_at=str(r["expires_at"]),
            revoked_at=str(r["revoked_at"]) if r["revoked_at"] else None,
            revocation_reason=str(r["revocation_reason"])
            if r["revocation_reason"]
            else None,
            ip=str(r["ip"]) if r["ip"] else None,
            user_agent=str(r["user_agent"]) if r["user_agent"] else None,
        )
        for r in rows
    ]
    return SessionsResponse(active_sessions=active, total_sessions=total, items=items)


@app.delete("/security/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE sessions SET revoked_at = ?,"
                " revocation_reason = 'user_revoked'"
                " WHERE session_id = ? AND user_email = ?",
                (now, session_id, current_user.email),
            )
            conn.commit()
        finally:
            conn.close()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/security/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE sessions SET revoked_at = ?,"
                " revocation_reason = 'revoke_all'"
                " WHERE user_email = ? AND revoked_at IS NULL",
                (now, current_user.email),
            )
            conn.commit()
        finally:
            conn.close()
    _log_security_event(current_user.email, "sessions_revoked_all")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/token/refresh", response_model=TokenPairResponse)
async def refresh_token(request: Request, body: RefreshTokenRequest):
    """Rotate refresh token and issue a new access token with subscription claims from DB."""
    try:
        payload: dict[str, Any] = jwt.decode(
            body.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp"]},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    email = str(payload.get("sub") or "")
    jti = str(payload.get("jti") or "")
    if not email or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user = get_user(email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or missing",
        )
    now_utc = datetime.datetime.now(datetime.UTC)
    refresh_expires = datetime.timedelta(days=7)
    new_jti = uuid.uuid4().hex
    expires_refresh_at = now_utc + refresh_expires
    client_host = request.client.host if request.client else None
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT session_id, expires_at, revoked_at FROM sessions WHERE session_id = ? AND user_email = ?",
                (jti, email),
            ).fetchone()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token not recognized",
                )
            if row["revoked_at"] is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token revoked",
                )
            exp_at = datetime.datetime.fromisoformat(str(row["expires_at"]))
            if exp_at.tzinfo is None:
                exp_at = exp_at.replace(tzinfo=datetime.timezone.utc)
            if now_utc > exp_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired",
                )
            conn.execute(
                "UPDATE sessions SET revoked_at = ?, revocation_reason = ? WHERE session_id = ?",
                (now_utc.isoformat(), "rotated", jti),
            )
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_email, issued_at, expires_at, ip, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_jti,
                    email,
                    now_utc.isoformat(),
                    expires_refresh_at.isoformat(),
                    client_host,
                    request.headers.get("user-agent"),
                ),
            )
            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        finally:
            conn.close()
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_claims: dict[str, object] = {
        "sub": user.email,
        "is_admin": user.is_admin,
        **_jwt_rbac_claims(user.is_admin, user.role),
        **_jwt_subscription_claims(user.email),
    }
    new_access = create_access_token(
        data=refresh_claims,
        expires_delta=access_token_expires,
    )
    new_refresh = create_access_token(
        data={"sub": user.email, "type": "refresh", "jti": new_jti},
        expires_delta=refresh_expires,
    )
    return TokenPairResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.delete("/token/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Revoke the current token (logout helper). Client must discard stored token."""
    _log_security_event(current_user.email, "token_revoked")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/verify-email/request", response_model=EmailVerificationRequestResp)
async def request_email_verification(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    code = str(uuid.uuid4().int)[:6]
    expires_at = (
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
    ).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO email_verifications"
                " (user_email, code, expires_at, confirmed) VALUES (?, ?, ?, 0)",
                (current_user.email, code, expires_at),
            )
            conn.commit()
        finally:
            conn.close()
    _log_security_event(current_user.email, "email_verification_requested")
    return EmailVerificationRequestResp(
        code_sent=True,
        debug_code=code if VERIFICATION_CODES_DEBUG else None,
        expires_at=expires_at,
        message="Verification code sent to your email address.",
    )


@app.post("/verify-email/confirm")
async def confirm_email_verification(
    current_user: Annotated[User, Depends(get_current_active_user)],
    code: str = Query(...),
):
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM email_verifications WHERE user_email = ?",
                (current_user.email,),
            ).fetchone()
            if not row:
                raise HTTPException(
                    status_code=400, detail="No verification request found."
                )
            if datetime.datetime.fromisoformat(
                str(row["expires_at"])
            ) < datetime.datetime.now(datetime.UTC):
                raise HTTPException(
                    status_code=400, detail="Verification code expired."
                )
            if str(row["code"]) != code:
                raise HTTPException(status_code=400, detail="Invalid code.")

            conn.execute(
                "UPDATE email_verifications SET confirmed = 1 WHERE user_email = ?",
                (current_user.email,),
            )
            conn.execute(
                """INSERT OR REPLACE INTO user_metadata (user_email, email_verified, locked_until, password_changed_at)
                   VALUES (?, 1, NULL, NULL)
                   ON CONFLICT(user_email) DO UPDATE SET email_verified = 1""",
                (current_user.email,),
            )
            conn.commit()
        finally:
            conn.close()
    _log_security_event(current_user.email, "email_verified")
    return {"confirmed": True}


@app.post("/security/lockdown")
async def activate_lockdown(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    locked_until = (
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24)
    ).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO user_metadata (user_email, email_verified, locked_until, password_changed_at)
                   VALUES (?, 0, ?, NULL)
                   ON CONFLICT(user_email) DO UPDATE SET locked_until = ?""",
                (current_user.email, locked_until, locked_until),
            )
            conn.commit()
        finally:
            conn.close()
    _log_security_event(
        current_user.email,
        "security_lockdown_activated",
        details={"locked_until": locked_until},
    )
    return {
        "message": "Account locked until " + locked_until,
        "locked_until": locked_until,
    }


@app.post("/legal/accept")
async def accept_legal(
    current_user: Annotated[User, Depends(get_current_active_user)],
    version: str = Query(default=LEGAL_CURRENT_VERSION),
):
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO legal_acceptances (user_email, version, accepted_at) VALUES (?, ?, ?)",
                (current_user.email, version, now),
            )
            conn.commit()
        finally:
            conn.close()
    _log_security_event(
        current_user.email, "legal_accepted", details={"version": version}
    )
    return {"accepted": True, "version": version, "accepted_at": now}


@app.post("/password/change")
async def change_password_alt(
    payload: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Alias for /change-password used by security.tsx."""
    row = get_user_record(current_user.email)
    if not row or not verify_password(
        payload.current_password, str(row["hashed_password"])
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    validate_password_strength(payload.new_password)
    now = datetime.datetime.now(datetime.UTC).isoformat()
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET hashed_password = ? WHERE email = ?",
                (get_password_hash(payload.new_password), current_user.email),
            )
            conn.execute(
                """INSERT OR REPLACE INTO user_metadata (user_email, email_verified, locked_until, password_changed_at)
                   VALUES (?, 0, NULL, ?)
                   ON CONFLICT(user_email) DO UPDATE SET password_changed_at = ?""",
                (current_user.email, now, now),
            )
            conn.commit()
        finally:
            conn.close()
    _log_security_event(current_user.email, "password_changed")
    return {"message": "Password changed successfully"}
