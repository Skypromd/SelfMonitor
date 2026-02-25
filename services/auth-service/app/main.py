from datetime import timedelta
import datetime
import io
import os
import sqlite3
import threading
from typing import Annotated, Optional, List

import pyotp
import qrcode
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr

# --- Configuration ---
# The secret key is now read from an environment variable for better security.
# A default value is provided for convenience in local development without Docker.
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "/tmp/auth.db")
AUTH_ADMIN_EMAIL = os.getenv("AUTH_ADMIN_EMAIL", "admin@example.com")
AUTH_ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin_password")
AUTH_BOOTSTRAP_ADMIN = os.getenv("AUTH_BOOTSTRAP_ADMIN", "false").lower() == "true"

app = FastAPI(
    title="Auth Service",
    description="Handles user authentication, registration, and token management.",
    version="1.0.0"
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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
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
    password: str

class User(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    is_two_factor_enabled: bool = False
    organization_id: Optional[str] = None
    role: str = "user"  # user, manager, admin, owner
    subscription_tier: str = "free"  # free, pro, enterprise

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

# --- Database ---
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_admin_user(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT email FROM users WHERE email = ?", (AUTH_ADMIN_EMAIL,)).fetchone()
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
        conn.commit()
        if AUTH_BOOTSTRAP_ADMIN:
            _seed_admin_user(conn)
        conn.close()


def reset_auth_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()


def get_user_record(email: str) -> Optional[dict]:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
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


def get_user(email: str) -> Optional[User]:
    row = get_user_record(email)
    if not row:
        return None
    return User(
        email=row["email"],
        is_active=bool(row["is_active"]),
        is_admin=bool(row["is_admin"]),
        is_two_factor_enabled=bool(row["is_two_factor_enabled"]),
    )

def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticates a user by checking their email and password."""
    row = get_user_record(email)
    if not row:
        return None
    if not verify_password(password, row["hashed_password"]):
        return None
    return User(
        email=row["email"],
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
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user", headers={"WWW-Authenticate": "Bearer"})
    return current_user

async def require_admin(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    A dependency that checks if the current user has admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

# --- Endpoints ---

@app.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    user_email = str(user_in.email)
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
    return User(email=user_email, is_active=True, is_admin=False, is_two_factor_enabled=False)


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- 2FA Check ---
    if user.is_two_factor_enabled:
        # We'll use the 'scope' field to pass the TOTP code, e.g., "totp:123456"
        totp_code = None
        if form_data.scopes:
            scope_parts = form_data.scopes[0].split(':')
            if len(scope_parts) == 2 and scope_parts[0] == 'totp':
                totp_code = scope_parts[1]

        if not totp_code:
            raise HTTPException(status_code=401, detail="2FA code required in 'scope' field (e.g., 'totp:123456')")

        row = get_user_record(user.email)
        totp = pyotp.TOTP(row["two_factor_secret"] if row else None)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- 2FA Endpoints ---

@app.get("/2fa/setup")
async def setup_two_factor_auth(current_user: Annotated[User, Depends(get_current_active_user)]):
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
        name=current_user.email,
        issuer_name="FinTech App"
    )

    # Generate QR code image
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


@app.post("/2fa/verify")
async def verify_two_factor_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
    totp_code: str = Query(..., description="The 6-digit code from the authenticator app.")
):
    """
    Verifies the TOTP code and enables 2FA for the user.
    """
    row = get_user_record(current_user.email)
    secret = row["two_factor_secret"] if row else None
    if not secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /2fa/setup first.")

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
    current_user: Annotated[User, Depends(get_current_active_user)]
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
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

@app.post("/users/{user_email}/deactivate", response_model=User)
async def deactivate_user(
    user_email: EmailStr,
    admin_user: Annotated[User, Depends(require_admin)]
):
    """
    Deactivates a user. This action is restricted to administrators.
    """
    user_to_deactivate = get_user(email=user_email)
    if not user_to_deactivate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user_to_deactivate.is_active:
        return user_to_deactivate # Already inactive, no change needed

    # Update the persistent user store directly.
    with db_lock:
        conn = _connect()
        conn.execute("UPDATE users SET is_active = 0 WHERE email = ?", (str(user_email),))
        conn.commit()
        conn.close()

    # Return the updated user model
    user_to_deactivate.is_active = False
    return user_to_deactivate


init_auth_db()

# === ENTERPRISE FEATURES ===

@app.post("/organizations")
async def create_organization(
    name: str,
    plan: str = "enterprise", 
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Create a new organization (available for Pro+ users)"""
    import uuid
    org_id = str(uuid.uuid4())[:8].upper()
    
    with db_lock:
        conn = _connect()
        try:
            # Create organization table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subscription_plan TEXT DEFAULT 'enterprise',
                    owner_email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create organization
            conn.execute(
                "INSERT INTO organizations (id, name, subscription_plan, owner_email) VALUES (?, ?, ?, ?)",
                (org_id, name, plan, current_user.email)
            )
            
            conn.commit()
            
            return {
                "id": org_id,
                "name": name,
                "subscription_plan": plan,
                "owner_email": current_user.email,
                "message": f"Enterprise organization '{name}' created! Monthly revenue: £{45 * 10} minimum"
            }
        except Exception as e:
            pass
        finally:
            conn.close()

@app.get("/enterprise/pricing")
async def get_enterprise_pricing():
    """Get current enterprise pricing plans"""
    return {
        "plans": {
            "team": {
                "price_per_user_per_month_gbp": 25,
                "min_users": 5, 
                "max_users": 20,
                "estimated_monthly_revenue": 625  # 25 * 25 avg users
            },
            "enterprise": {
                "price_per_user_per_month_gbp": 45,
                "min_users": 10,
                "max_users": 500,
                "estimated_monthly_revenue": 2250  # 50 * 45 avg users
            }
        },
        "roi_metrics": {
            "customer_lifetime_value": 12600,  # £45 * 12 months * 23.33 avg retention
            "enterprise_arpu_improvement": "3x higher than individual plans"
        }
    }
