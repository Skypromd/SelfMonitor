import os

from fastapi import Depends, FastAPI, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db

app = FastAPI(
    title="User Profile Service",
    description="Manages user profile data.",
    version="1.0.0"
)

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"


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

# @app.on_event("startup")
# async def startup():
#     # This logic is now handled by Alembic migrations.
#     # You should run `alembic upgrade head` before starting the application.
#     pass

# --- Endpoints ---
@app.get("/profiles/me", response_model=schemas.UserProfile)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id), 
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the profile for the currently authenticated user from the database."""
    db_profile = await crud.get_profile_by_user_id(db, user_id=user_id)
    if db_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return db_profile

@app.put("/profiles/me", response_model=schemas.UserProfile)
async def create_or_update_my_profile(
    profile_update: schemas.UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new profile or updates an existing one for the authenticated user in the database."""
    db_profile = await crud.create_or_update_profile(db, user_id=user_id, profile=profile_update)
    return db_profile
