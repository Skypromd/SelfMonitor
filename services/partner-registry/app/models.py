import datetime
import uuid

from sqlalchemy import CheckConstraint, JSON, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String

from .database import Base


class Partner(Base):
    __tablename__ = "partners"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    services_offered = Column(JSON, nullable=False)
    website = Column(String, nullable=False)
    qualified_lead_fee_gbp = Column(Float, nullable=False, default=12.0)
    converted_lead_fee_gbp = Column(Float, nullable=False, default=35.0)


class HandoffLead(Base):
    __tablename__ = "handoff_leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('initiated', 'qualified', 'rejected', 'converted')",
            name="ck_handoff_leads_status_allowed",
        ),
        Index("ix_handoff_leads_status", "status"),
        Index("ix_handoff_leads_partner_created_at", "partner_id", "created_at"),
        Index("ix_handoff_leads_user_partner_created_at", "user_id", "partner_id", "created_at"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    partner_id = Column(String, ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="initiated")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('generated', 'issued', 'paid', 'void')",
            name="ck_billing_invoices_status_allowed",
        ),
        Index("ix_billing_invoices_created_at", "created_at"),
        Index("ix_billing_invoices_status", "status"),
        Index("ix_billing_invoices_invoice_number", "invoice_number", unique=True),
        Index("ix_billing_invoices_due_date", "due_date"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    invoice_number = Column(String(length=32), nullable=False)
    generated_by_user_id = Column(String, nullable=False, index=True)
    partner_id = Column(String, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    due_date = Column(Date, nullable=False)
    currency = Column(String(length=3), nullable=False, default="GBP")
    statuses = Column(JSON, nullable=False)
    total_amount_gbp = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="generated")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )


class BillingInvoiceLine(Base):
    __tablename__ = "billing_invoice_lines"
    __table_args__ = (
        Index("ix_billing_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_billing_invoice_lines_partner_id", "partner_id"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False)
    partner_id = Column(String, nullable=False)
    partner_name = Column(String, nullable=False)
    qualified_leads = Column(Integer, nullable=False, default=0)
    converted_leads = Column(Integer, nullable=False, default=0)
    unique_users = Column(Integer, nullable=False, default=0)
    qualified_lead_fee_gbp = Column(Float, nullable=False, default=0.0)
    converted_lead_fee_gbp = Column(Float, nullable=False, default=0.0)
    amount_gbp = Column(Float, nullable=False, default=0.0)


class NPSResponse(Base):
    __tablename__ = "nps_responses"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 10", name="ck_nps_responses_score_range"),
        Index("ix_nps_responses_created_at", "created_at"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    feedback = Column(String, nullable=True)
    context_tag = Column(String(length=64), nullable=True)
    locale = Column(String(length=16), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )

