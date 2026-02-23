from sqlalchemy import Boolean, Column, Float, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import datetime

Base = declarative_base()

class ReferralCode(Base):
    __tablename__ = "referral_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    campaign_type = Column(String(50), nullable=False, default="standard")
    reward_amount = Column(Float, nullable=False, default=25.0)
    max_uses = Column(Integer, nullable=False, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationship to usage records
    usages = relationship("ReferralUsage", back_populates="referral_code")

class ReferralUsage(Base):
    __tablename__ = "referral_usages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referral_code_id = Column(UUID(as_uuid=True), ForeignKey("referral_codes.id"), nullable=False)
    referred_user_id = Column(String, nullable=False)
    referrer_user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reward_paid = Column(Boolean, default=False)
    
    # Relationships
    referral_code = relationship("ReferralCode", back_populates="usages")

class ReferralCampaign(Base):
    __tablename__ = "referral_campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    reward_multiplier = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)