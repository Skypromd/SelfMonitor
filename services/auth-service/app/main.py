from fastapi import FastAPI, Depends, HTTPException, status, Response, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional, Annotated, Dict
from datetime import timedelta
import datetime
import os
import pyotp
import qrcode
import io
from prometheus_fastapi_instrumentator import Instrumentator

# --- Configuration ---
# The secret key is now read from an environment variable for better security.
# A default value is provided for convenience in local development without Docker.
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- "Database" ---

# In-memory user store for demonstration purposes
# NOTE: We are adding 2FA fields to the user data.
fake_users_db: Dict[EmailStr, Dict] = {
    "admin@example.com": {
        "user_data": {
            "email": "admin@example.com",
            "is_active": True,
            "is_admin": True,
            "two_factor_secret": None, # Secret key for TOTP
            "is_two_factor_enabled": False,
        },
        "hashed_password": pwd_context.hash("admin_password"),
    }
}

def get_user(email: str) -> Optional[User]:
    if email in fake_users_db:
        user_dict = fake_users_db[email]['user_data']
        return User(**user_dict)
    return None

def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticates a user by checking their email and password."""
    user = get_user(email)
    if not user:
        return None
    if not verify_password(password, fake_users_db[email]["hashed_password"]):
        return None
    return user

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
    if user_email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_data = {
        "email": user_email,
        "is_active": True,
        "is_admin": False, # New users are not admins by default
        "two_factor_secret": None,
        "is_two_factor_enabled": False,
    }

    fake_users_db[user_email] = {
        "user_data": user_data,
        "hashed_password": pwd_context.hash(user_in.password),
    }
    return User(**user_data)


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

        totp = pyotp.TOTP(fake_users_db[user.email]["user_data"]["two_factor_secret"])
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
    fake_users_db[current_user.email]["user_data"]["two_factor_secret"] = secret

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
    secret = fake_users_db[current_user.email]["user_data"]["two_factor_secret"]
    if not secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /2fa/setup first.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(totp_code):
        raise HTTPException(status_code=400, detail="Invalid code.")

    # Enable 2FA for the user
    fake_users_db[current_user.email]["user_data"]["is_two_factor_enabled"] = True
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
    fake_users_db[current_user.email]["user_data"]["is_two_factor_enabled"] = False
    fake_users_db[current_user.email]["user_data"]["two_factor_secret"] = None

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

    # Update the "database" directly
    fake_users_db[user_email]['user_data']['is_active'] = False

    # Return the updated user model
    user_to_deactivate.is_active = False
    return user_to_deactivate
