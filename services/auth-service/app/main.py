import datetime
import io
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Annotated, Any, Optional

import pyotp
import qrcode
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)

# --- Configuration ---
# The secret key is now read from an environment variable for better security.
# A default value is provided for convenience in local development without Docker.
SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "/tmp/auth.db")
AUTH_ADMIN_EMAIL = os.getenv("AUTH_ADMIN_EMAIL", "admin@example.com")
AUTH_ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin_password")
AUTH_BOOTSTRAP_ADMIN = os.getenv("AUTH_BOOTSTRAP_ADMIN", "false").lower() == "true"

app = FastAPI(
    title="Auth Service",
    description="Handles user authentication, registration, and token management.",
    version="1.0.0",
)

# --- Observability ---
# This line adds an instrumentator that exposes a /metrics endpoint
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- Security Utils ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
db_lock = threading.Lock()


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


# --- Account Lockout ---
_login_attempts: dict[str, list[float]] = defaultdict(list)
LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes


def check_account_lockout(email: str) -> None:
    now = time.time()
    attempts = _login_attempts[email]
    _login_attempts[email] = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    if len(_login_attempts[email]) >= LOCKOUT_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked. Try again in 15 minutes.",
        )


def record_failed_attempt(email: str) -> None:
    _login_attempts[email].append(time.time())


def clear_failed_attempts(email: str) -> None:
    _login_attempts.pop(email, None)


def create_access_token(
    data: dict[str, object], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode: dict[str, object] = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Models ---


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    plan: str = "free"


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


class TokenData(BaseModel):
    email: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# --- Database ---
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_admin_user(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT email FROM users WHERE email = ?", (AUTH_ADMIN_EMAIL,)
    ).fetchone()
    if existing:
        return
    conn.execute(
        """
        INSERT INTO users (email, hashed_password, is_active, is_admin, is_two_factor_enabled, two_factor_secret)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (AUTH_ADMIN_EMAIL, get_password_hash(AUTH_ADMIN_PASSWORD), 1, 1, 0, None),
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
        conn.commit()
        if AUTH_BOOTSTRAP_ADMIN:
            _seed_admin_user(conn)
        conn.close()


def reset_auth_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
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
PLAN_HIERARCHY = {"free": 0, "starter": 1, "pro": 2, "business": 3}
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
    status = "active"
    if plan != "free":
        trial_end = (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=TRIAL_DAYS)
        ).isoformat()
        status = "trialing"
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO subscriptions (user_email, plan, status, trial_end, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (email, plan, status, trial_end, now, now),
            )
            conn.commit()
        finally:
            conn.close()
    return {"user_email": email, "plan": plan, "status": status, "trial_end": trial_end}


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


def get_user(email: str) -> Optional[User]:
    row = get_user_record(email)
    if not row:
        return None
    return User(
        email=str(row["email"]),
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        is_two_factor_enabled=bool(row["is_two_factor_enabled"]),
    )


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticates a user by checking their email and password."""
    row = get_user_record(email)
    if not row:
        return None
    if not verify_password(password, str(row["hashed_password"])):
        return None
    return User(
        email=str(row["email"]),
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        is_two_factor_enabled=bool(row["is_two_factor_enabled"]),
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
    except JWTError:
        raise credentials_exception
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
    """
    A dependency that checks if the current user has admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


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
    valid_plans = {"free", "starter", "pro", "business"}
    plan = user_in.plan if user_in.plan in valid_plans else "free"
    create_subscription(user_email, plan)
    return User(
        email=user_email, is_active=True, is_admin=False, is_two_factor_enabled=False
    )


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    check_account_lockout(form_data.username)

    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        record_failed_attempt(form_data.username)
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

    clear_failed_attempts(form_data.username)
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
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
        name=current_user.email, issuer_name="SelfMonitor"
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "issuer": "SelfMonitor",
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
    user_email: EmailStr, admin_user: Annotated[User, Depends(require_admin)]
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
        "transactions_per_month": 200,
        "ai_categorization": False,
        "receipt_ocr": False,
        "cash_flow_forecast": False,
        "tax_calculator": "basic",
        "hmrc_submission": False,
        "smart_search": False,
        "mortgage_reports": False,
        "advanced_analytics": False,
        "api_access": False,
        "team_members": 1,
        "white_label": False,
    },
    "starter": {
        "bank_connections": 3,
        "transactions_per_month": 1000,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": False,
        "smart_search": False,
        "mortgage_reports": False,
        "advanced_analytics": False,
        "api_access": False,
        "team_members": 1,
        "white_label": False,
    },
    "pro": {
        "bank_connections": 3,
        "transactions_per_month": 5000,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": True,
        "smart_search": True,
        "mortgage_reports": True,
        "advanced_analytics": True,
        "api_access": True,
        "team_members": 1,
        "white_label": False,
    },
    "business": {
        "bank_connections": 3,
        "transactions_per_month": 999999,
        "ai_categorization": True,
        "receipt_ocr": True,
        "cash_flow_forecast": True,
        "tax_calculator": "full",
        "hmrc_submission": True,
        "smart_search": True,
        "mortgage_reports": True,
        "advanced_analytics": True,
        "api_access": True,
        "team_members": 5,
        "white_label": True,
    },
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
    plan: str = Query(..., pattern="^(starter|pro|business)$"),
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
                "price_gbp": 9,
                "features": PLAN_FEATURES["starter"],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_gbp": 19,
                "features": PLAN_FEATURES["pro"],
                "popular": True,
            },
            {
                "id": "business",
                "name": "Business",
                "price_gbp": 39,
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
        for p in ["starter", "pro", "business"]:
            pf: dict[str, Any] = PLAN_FEATURES[p]
            val: Any = pf.get(feature, False)
            if val and val != "basic":
                min_plan = p
                break
        return {"allowed": False, "required_plan": min_plan, "current_plan": plan}
    return {"allowed": True, "current_plan": plan}


init_auth_db()

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
            raise HTTPException(status_code=500, detail="Failed to create organization")
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
