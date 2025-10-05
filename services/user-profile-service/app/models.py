from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.sql import func
from .database import Base

class UserProfile(Base):
    """SQLAlchemy model for the user_profiles table."""
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
