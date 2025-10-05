from pydantic import BaseModel
from typing import Optional
import datetime

class UserProfileBase(BaseModel):
    """Base schema for user profile data."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None

class UserProfileUpdate(UserProfileBase):
    """Schema for updating a profile."""
    pass

class UserProfile(UserProfileBase):
    """Schema for returning a profile, includes all fields."""
    user_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        # This allows the model to be created from ORM objects
        orm_mode = True
