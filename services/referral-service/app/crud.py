from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from sqlalchemy.orm import selectinload
import uuid
import datetime
from typing import Optional, List

from . import models, schemas

async def create_referral_code(db: AsyncSession, referral_code: schemas.ReferralCodeCreate) -> models.ReferralCode:
    db_code = models.ReferralCode(**referral_code.dict())
    db.add(db_code)
    await db.commit()
    await db.refresh(db_code)
    return db_code

async def get_referral_code_by_user(db: AsyncSession, user_id: str) -> Optional[models.ReferralCode]:
    result = await db.execute(
        select(models.ReferralCode).where(models.ReferralCode.user_id == user_id)
        .where(models.ReferralCode.is_active == True)
    )
    return result.scalar_one_or_none()

async def get_referral_code_by_code(db: AsyncSession, code: str) -> Optional[models.ReferralCode]:
    result = await db.execute(
        select(models.ReferralCode).where(models.ReferralCode.code == code)
    )
    return result.scalar_one_or_none()

async def get_referral_usage_count(db: AsyncSession, referral_code_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(models.ReferralUsage.id))
        .where(models.ReferralUsage.referral_code_id == referral_code_id)
    )
    return result.scalar()

async def create_referral_usage(db: AsyncSession, usage: schemas.ReferralUsageCreate) -> models.ReferralUsage:
    db_usage = models.ReferralUsage(**usage.dict())
    db.add(db_usage)
    await db.commit()
    await db.refresh(db_usage)
    return db_usage

async def get_referral_statistics(db: AsyncSession, referral_code_id: uuid.UUID) -> schemas.ReferralStats:
    # Get total referrals
    total_result = await db.execute(
        select(func.count(models.ReferralUsage.id))
        .where(models.ReferralUsage.referral_code_id == referral_code_id)
    )
    total_referrals = total_result.scalar()
    
    # Get this month's conversions
    current_month_start = datetime.datetime.now(datetime.UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_result = await db.execute(
        select(func.count(models.ReferralUsage.id))
        .where(models.ReferralUsage.referral_code_id == referral_code_id)
        .where(models.ReferralUsage.created_at >= current_month_start)
    )
    monthly_conversions = monthly_result.scalar()
    
    # Get referral code details for reward calculation
    code_result = await db.execute(
        select(models.ReferralCode).where(models.ReferralCode.id == referral_code_id)
    )
    referral_code = code_result.scalar_one_or_none()
    
    reward_amount = referral_code.reward_amount if referral_code else 0.0
    total_earned = total_referrals * reward_amount
    
    # For now, assume 20% pending (realistic for payment processing)
    pending_rewards = total_earned * 0.2
    
    return schemas.ReferralStats(
        total_referrals=total_referrals,
        active_referrals=total_referrals,
        total_earned=total_earned,
        pending_rewards=pending_rewards,
        conversions_this_month=monthly_conversions
    )

async def get_referral_leaderboard(db: AsyncSession, limit: int = 10) -> List[dict]:
    # Complex query to get top referrers
    result = await db.execute(text("""
        SELECT 
            rc.user_id,
            rc.code,
            COUNT(ru.id) as referral_count,
            SUM(rc.reward_amount) as total_earned
        FROM referral_codes rc
        LEFT JOIN referral_usages ru ON rc.id = ru.referral_code_id
        WHERE rc.is_active = true
        GROUP BY rc.user_id, rc.code, rc.reward_amount
        ORDER BY referral_count DESC, total_earned DESC
        LIMIT :limit
    """), {"limit": limit})
    
    return [
        {
            "user_id": row.user_id,
            "code": row.code,
            "referral_count": row.referral_count or 0,
            "total_earned": float(row.total_earned or 0.0)
        }
        for row in result
    ]

async def get_user_referral_rank(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(text("""
        WITH user_stats AS (
            SELECT 
                rc.user_id,
                COUNT(ru.id) as referral_count
            FROM referral_codes rc
            LEFT JOIN referral_usages ru ON rc.id = ru.referral_code_id
            WHERE rc.is_active = true
            GROUP BY rc.user_id
        ),
        ranked_users AS (
            SELECT 
                user_id,
                referral_count,
                ROW_NUMBER() OVER (ORDER BY referral_count DESC) as rank
            FROM user_stats
        )
        SELECT rank FROM ranked_users WHERE user_id = :user_id
    """), {"user_id": user_id})
    
    rank_result = result.scalar()
    return rank_result or 999

async def get_campaign_by_id(db: AsyncSession, campaign_id: str) -> Optional[models.ReferralCampaign]:
    try:
        campaign_uuid = uuid.UUID(campaign_id)
    except ValueError:
        return None
        
    result = await db.execute(
        select(models.ReferralCampaign).where(models.ReferralCampaign.id == campaign_uuid)
    )
    return result.scalar_one_or_none()

async def update_referral_code_for_campaign(
    db: AsyncSession, 
    user_id: str, 
    campaign_id: str, 
    multiplier: float
) -> models.ReferralCode:
    # Get existing code or create new
    referral_code = await get_referral_code_by_user(db, user_id)
    
    if referral_code:
        # Update with campaign multiplier
        referral_code.reward_amount = 25.0 * multiplier
        referral_code.campaign_type = f"campaign_{campaign_id}"
    else:
        # Create new code for campaign
        new_code = str(uuid.uuid4())[:8].upper()
        referral_code = models.ReferralCode(
            user_id=user_id,
            code=new_code,
            campaign_type=f"campaign_{campaign_id}",
            reward_amount=25.0 * multiplier
        )
        db.add(referral_code)
    
    await db.commit()
    await db.refresh(referral_code)
    return referral_code