from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime

class UserProfileBase(BaseModel):
    """Base schema for user profile data."""
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[datetime.date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = Field(default="UTC", description="User timezone")
    language: Optional[str] = Field(default="en", description="User language preference")
    currency: Optional[str] = Field(default="USD", description="User currency preference")


class SubscriptionBase(BaseModel):
    subscription_plan: str = Field(default="free", description="Subscription plan (free/pro).")
    subscription_status: str = Field(default="active", description="Subscription status.")
    billing_cycle: str = Field(default="monthly", description="Billing cycle (monthly).")
    current_period_start: Optional[datetime.date] = None
    current_period_end: Optional[datetime.date] = None
    monthly_close_day: Optional[int] = Field(default=1, ge=1, le=28)

class UserProfileUpdate(UserProfileBase):
    """Schema for updating a profile."""
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    billing_cycle: Optional[str] = None
    pass

class UserProfileCreate(UserProfileBase):
    """Schema for creating a new profile."""
    user_id: str
    subscription_plan: Optional[str] = Field(default="free", description="Subscription plan")
    subscription_status: Optional[str] = Field(default="active", description="Subscription status")
    billing_cycle: Optional[str] = Field(default="monthly", description="Billing cycle")

class UserProfile(UserProfileBase):
    """Schema for returning a profile, includes all fields."""
    user_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
