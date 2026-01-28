from sqlalchemy import Column, String, Date, DateTime, Integer
from sqlalchemy.sql import func
from .database import Base

class UserProfile(Base):
    """SQLAlchemy model for the user_profiles table."""
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    subscription_plan = Column(String, nullable=False, default="free")
    subscription_status = Column(String, nullable=False, default="active")
    billing_cycle = Column(String, nullable=False, default="monthly")
    current_period_start = Column(Date, nullable=True)
    current_period_end = Column(Date, nullable=True)
    monthly_close_day = Column(Integer, nullable=True, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
