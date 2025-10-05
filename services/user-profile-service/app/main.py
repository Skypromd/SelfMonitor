from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db

app = FastAPI(
    title="User Profile Service",
    description="Manages user profile data.",
    version="1.0.0"
)

# --- Placeholder Security ---
def fake_auth_check() -> str:
    """A fake dependency to simulate user authentication and return a user ID."""
    return "fake-user-123"

# @app.on_event("startup")
# async def startup():
#     # This logic is now handled by Alembic migrations.
#     # You should run `alembic upgrade head` before starting the application.
#     pass

# --- Endpoints ---
@app.get("/profiles/me", response_model=schemas.UserProfile)
async def get_my_profile(
    user_id: str = Depends(fake_auth_check), 
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
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new profile or updates an existing one for the authenticated user in the database."""
    db_profile = await crud.create_or_update_profile(db, user_id=user_id, profile=profile_update)
    return db_profile
