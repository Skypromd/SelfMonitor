import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from . import billing_credit, crud, models, schemas
from .database import engine, get_db

app = FastAPI(
    title="Referral Service",
    description="Manages referral codes, rewards, and viral growth campaigns.",
    version="1.0.0"
)

# --- Security ---
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- Configuration ---
USER_PROFILE_SERVICE_URL = os.getenv("USER_PROFILE_SERVICE_URL", "http://localhost:8001")

def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    return user_id

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


def _require_internal_token(x_internal_token: str | None) -> None:
    if not billing_credit.INTERNAL_SERVICE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="internal_calls_not_configured",
        )
    if not x_internal_token or x_internal_token != billing_credit.INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


@app.post("/internal/apply-signup-referral")
async def internal_apply_signup_referral(
    body: schemas.InternalReferralSignup,
    db: AsyncSession = Depends(get_db),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
):
    """Called by auth-service after user registers with ?ref= (no JWT yet)."""
    _require_internal_token(x_internal_token)
    ref_email = str(body.referee_email).lower().strip()
    code = body.code.strip().upper()
    if await crud.count_usages_for_referred_user(db, ref_email) > 0:
        return {"status": "noop", "detail": "referral_already_recorded"}
    referral_code = await crud.get_referral_code_by_code(db, code)
    if not referral_code or not referral_code.is_active:
        raise HTTPException(status_code=404, detail="Invalid or expired referral code")
    if referral_code.user_id.lower().strip() == ref_email:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")
    usage_count = await crud.get_referral_usage_count(db, referral_code.id)
    if usage_count >= referral_code.max_uses:
        raise HTTPException(status_code=400, detail="Referral code has reached maximum uses")
    usage = await crud.create_referral_usage(
        db,
        schemas.ReferralUsageCreate(
            referral_code_id=referral_code.id,
            referred_user_id=ref_email,
            referrer_user_id=referral_code.user_id,
        ),
    )
    await billing_credit.grant_referral_pair_credits(
        referrer_user_id=referral_code.user_id,
        referee_user_id=ref_email,
        amount_gbp=float(referral_code.reward_amount),
        usage_id=str(usage.id),
    )
    return {
        "status": "ok",
        "referrer_reward": referral_code.reward_amount,
        "referee_reward": referral_code.reward_amount,
    }


@app.get("/internal/top-referrers")
async def internal_top_referrers(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
):
    _require_internal_token(x_internal_token)
    items = await crud.top_referrers_in_month(db, year, month, limit)
    return {"items": items, "year": year, "month": month}

@app.post("/referral-codes", response_model=schemas.ReferralCode)
async def create_referral_code(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate a unique referral code for the user"""
    # Check if user already has an active referral code
    existing_code = await crud.get_referral_code_by_user(db, user_id)
    if existing_code and existing_code.is_active:
        return existing_code

    # Generate new 6-character code
    code = str(uuid.uuid4())[:8].upper()

    db_code = await crud.create_referral_code(db, schemas.ReferralCodeCreate(
        user_id=user_id,
        code=code,
        campaign_type="standard",
        reward_amount=25.0,  # £25 credit for both referrer and referee
        max_uses=50
    ))
    return db_code


@app.get("/me/referral-code", response_model=Optional[schemas.ReferralCode])
async def get_my_referral_code(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's referral code, or null if none exists yet."""
    return await crud.get_referral_code_by_user(db, user_id)


@app.post("/validate-referral")
async def validate_referral_code(
    request: schemas.ReferralValidation,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Validate and apply a referral code during registration"""
    if await crud.count_usages_for_referred_user(db, user_id) > 0:
        raise HTTPException(
            status_code=400,
            detail="Referral rewards already applied for this account",
        )
    code = request.code.strip().upper()
    referral_code = await crud.get_referral_code_by_code(db, code)
    if not referral_code or not referral_code.is_active:
        raise HTTPException(status_code=404, detail="Invalid or expired referral code")

    # Check if user can use this code
    if referral_code.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")

    # Check max uses
    usage_count = await crud.get_referral_usage_count(db, referral_code.id)
    if usage_count >= referral_code.max_uses:
        raise HTTPException(status_code=400, detail="Referral code has reached maximum uses")

    # Create referral usage record
    usage = await crud.create_referral_usage(db, schemas.ReferralUsageCreate(
        referral_code_id=referral_code.id,
        referred_user_id=user_id,
        referrer_user_id=referral_code.user_id
    ))
    await billing_credit.grant_referral_pair_credits(
        referrer_user_id=referral_code.user_id,
        referee_user_id=user_id,
        amount_gbp=float(referral_code.reward_amount),
        usage_id=str(usage.id),
    )

    return {
        "status": "valid",
        "referrer_reward": referral_code.reward_amount,
        "referee_reward": referral_code.reward_amount,
        "message": f"Congratulations! You and your referrer will each get £{referral_code.reward_amount} credit"
    }

@app.get("/stats", response_model=schemas.ReferralStats)
async def get_referral_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get referral statistics for the user"""
    referral_code = await crud.get_referral_code_by_user(db, user_id)
    if not referral_code:
        return schemas.ReferralStats(
            total_referrals=0,
            active_referrals=0,
            total_earned=0.0,
            pending_rewards=0.0,
            conversions_this_month=0
        )

    stats = await crud.get_referral_statistics(db, referral_code.id)
    return stats

@app.get("/leaderboard")
async def get_referral_leaderboard(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get top referrers leaderboard (gamification)"""
    leaderboard = await crud.get_referral_leaderboard(db, limit)

    # Find current user's position
    user_position = await crud.get_user_referral_rank(db, user_id)

    return {
        "leaderboard": leaderboard,
        "your_position": user_position,
        "rewards": {
            "monthly_champion": "3 months Pro free",
            "top_3": "1 month Pro free",
            "top_10": "£50 credit"
        }
    }

@app.post("/campaigns/{campaign_id}/join")
async def join_referral_campaign(
    campaign_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Join special referral campaigns (2x rewards, time-limited, etc.)"""
    campaign = await crud.get_campaign_by_id(db, campaign_id)
    if not campaign or not campaign.is_active:
        raise HTTPException(status_code=404, detail="Campaign not found or inactive")

    if campaign.end_date and campaign.end_date < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Campaign has ended")

    # Create/update user's referral code for this campaign
    updated_code = await crud.update_referral_code_for_campaign(
        db, user_id, campaign_id, campaign.reward_multiplier
    )

    return {
        "campaign_name": campaign.name,
        "description": campaign.description,
        "multiplier": f"{campaign.reward_multiplier}x",
        "end_date": campaign.end_date,
        "your_code": updated_code.code
    }
