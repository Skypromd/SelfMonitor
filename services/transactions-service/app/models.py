import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, JSON, String, Uuid
from sqlalchemy.sql import func

from .database import Base


class UserBusiness(Base):
    __tablename__ = "user_businesses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    display_name = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Uuid(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    business_id = Column(Uuid(as_uuid=True), ForeignKey("user_businesses.id"), nullable=True, index=True)
    account_id = Column(Uuid(as_uuid=True), nullable=False, index=True)

    provider_transaction_id = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)

    category = Column(String, nullable=True)
    tax_category = Column(String, nullable=True)
    business_use_percent = Column(Float, nullable=True)
    reconciliation_status = Column(String, nullable=True)
    ignored_candidate_ids = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CISRecord(Base):
    __tablename__ = "cis_records"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    contractor_name = Column(String(300), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    gross_total = Column(Float, nullable=False)
    materials_total = Column(Float, nullable=False, default=0.0)
    cis_deducted_total = Column(Float, nullable=False)
    net_paid_total = Column(Float, nullable=False)
    evidence_status = Column(String(64), nullable=False)
    document_id = Column(String(128), nullable=True)
    source = Column(String(64), nullable=False)
    matched_bank_transaction_ids = Column(JSON, nullable=True)
    attestation_json = Column(JSON, nullable=True)
    report_status = Column(String(64), nullable=False, default="draft")
    reconciliation_status = Column(String(32), nullable=True)
    bank_net_observed_gbp = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CISObligation(Base):
    __tablename__ = "cis_obligations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    cis_tax_month_label = Column(String(32), nullable=False)
    contractor_key = Column(String(80), nullable=False)
    status = Column(String(32), nullable=False, default="MISSING")
    snooze_until = Column(Date, nullable=True)
    last_reminded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CISReviewTask(Base):
    __tablename__ = "cis_review_tasks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String(64), nullable=False, default="open")
    suspected_transaction_id = Column(Uuid(as_uuid=True), nullable=True)
    cis_record_id = Column(Uuid(as_uuid=True), nullable=True)
    payer_label = Column(String(300), nullable=True)
    suspect_reason = Column(String(500), nullable=True)
    next_reminder_at = Column(Date, nullable=True)
    reminder_meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccountantDelegation(Base):
    __tablename__ = "accountant_delegations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_user_id = Column(String, nullable=False, index=True)
    accountant_user_id = Column(String, nullable=False)
    scopes = Column(JSON, nullable=False)
    can_submit_hmrc = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
