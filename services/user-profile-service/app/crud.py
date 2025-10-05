from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def get_profile_by_user_id(db: AsyncSession, user_id: str):
    """Fetches a user profile from the database by user_id."""
    result = await db.execute(select(models.UserProfile).filter(models.UserProfile.user_id == user_id))
    return result.scalars().first()

async def create_or_update_profile(db: AsyncSession, user_id: str, profile: schemas.UserProfileUpdate):
    """Creates or updates a user profile in the database."""
    existing_profile = await get_profile_by_user_id(db, user_id)
    update_data = profile.dict(exclude_unset=True)

    if existing_profile:
        # Update existing profile
        for key, value in update_data.items():
            setattr(existing_profile, key, value)
        db_profile = existing_profile
    else:
        # Create new profile
        db_profile = models.UserProfile(**profile.dict(exclude_unset=True), user_id=user_id)
        db.add(db_profile)

    await db.commit()
    await db.refresh(db_profile)
    return db_profile
