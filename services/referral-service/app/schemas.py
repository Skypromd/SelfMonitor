from pydantic import BaseModel, Field
from typing import Optional
import datetime
import uuid

class ReferralCodeBase(BaseModel):
    code: str
    campaign_type: str = "standard"
    reward_amount: float = 25.0
    max_uses: int = 50

class ReferralCodeCreate(ReferralCodeBase):
    user_id: str

class ReferralCode(ReferralCodeBase):
    id: uuid.UUID
    user_id: str
    is_active: bool = True
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    
    class Config:
        from_attributes = True

class ReferralUsageCreate(BaseModel):
    referral_code_id: uuid.UUID
    referred_user_id: str
    referrer_user_id: str

class ReferralUsage(ReferralUsageCreate):
    id: uuid.UUID
    created_at: datetime.datetime
    reward_paid: bool = False
    
    class Config:
        from_attributes = True

class ReferralValidation(BaseModel):
    code: str

class ReferralStats(BaseModel):
    total_referrals: int
    active_referrals: int
    total_earned: float
    pending_rewards: float
    conversions_this_month: int

class ReferralCampaign(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    reward_multiplier: float = 1.0
    is_active: bool = True
    start_date: datetime.datetime
    end_date: Optional[datetime.datetime] = None
    
    class Config:
        from_attributes = True