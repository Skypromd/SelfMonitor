from sqlalchemy import Column, String, Date, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    provider_transaction_id = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)

    category = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
