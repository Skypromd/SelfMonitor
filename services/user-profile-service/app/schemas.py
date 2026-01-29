from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import datetime

class UserProfileBase(BaseModel):
    """Base schema for user profile data."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None


class SubscriptionBase(BaseModel):
    subscription_plan: str = Field(default="free", description="Subscription plan (free/pro).")
    subscription_status: str = Field(default="active", description="Subscription status.")
    billing_cycle: str = Field(default="monthly", description="Billing cycle (monthly).")
    current_period_start: Optional[datetime.date] = None
    current_period_end: Optional[datetime.date] = None
    monthly_close_day: Optional[int] = Field(default=1, ge=1, le=28)

class UserProfileUpdate(UserProfileBase):
    """Schema for updating a profile."""
    pass

class UserProfile(UserProfileBase):
    """Schema for returning a profile, includes all fields."""
    user_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionUpdate(BaseModel):
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    billing_cycle: Optional[str] = None
    current_period_start: Optional[datetime.date] = None
    current_period_end: Optional[datetime.date] = None
    monthly_close_day: Optional[int] = Field(default=None, ge=1, le=28)


class SubscriptionResponse(SubscriptionBase):
    user_id: str

    model_config = ConfigDict(from_attributes=True)
