from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import datetime

async def get_profile_by_user_id(db: AsyncSession, user_id: str):
    """Fetches a user profile from the database by user_id."""
    result = await db.execute(select(models.UserProfile).filter(models.UserProfile.user_id == user_id))
    return result.scalars().first()

def _apply_subscription_defaults(profile: models.UserProfile) -> bool:
    changed = False
    today = datetime.date.today()
    if not profile.subscription_plan:
        profile.subscription_plan = "free"
        changed = True
    if not profile.subscription_status:
        profile.subscription_status = "active"
        changed = True
    if not profile.billing_cycle:
        profile.billing_cycle = "monthly"
        changed = True
    if profile.current_period_start is None:
        profile.current_period_start = today
        changed = True
    if profile.current_period_end is None:
        profile.current_period_end = today + datetime.timedelta(days=30)
        changed = True
    if profile.monthly_close_day is None:
        profile.monthly_close_day = 1
        changed = True
    return changed

async def get_or_create_profile(db: AsyncSession, user_id: str):
    profile = await get_profile_by_user_id(db, user_id)
    if profile is None:
        profile = models.UserProfile(user_id=user_id)
        _apply_subscription_defaults(profile)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    if _apply_subscription_defaults(profile):
        await db.commit()
        await db.refresh(profile)
    return profile

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

    _apply_subscription_defaults(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

async def update_subscription(db: AsyncSession, user_id: str, update: schemas.SubscriptionUpdate):
    profile = await get_or_create_profile(db, user_id)
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    if profile.current_period_start is None or profile.current_period_end is None:
        _apply_subscription_defaults(profile)

    await db.commit()
    await db.refresh(profile)
    return profile
