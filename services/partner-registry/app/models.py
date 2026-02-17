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


class SelfEmployedInvoice(Base):
    __tablename__ = "self_employed_invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'issued', 'paid', 'overdue', 'void')",
            name="ck_self_employed_invoices_status_allowed",
        ),
        CheckConstraint("tax_rate_percent >= 0 AND tax_rate_percent <= 100", name="ck_self_employed_invoices_tax_rate"),
        CheckConstraint("subtotal_gbp >= 0", name="ck_self_employed_invoices_subtotal_non_negative"),
        CheckConstraint("tax_amount_gbp >= 0", name="ck_self_employed_invoices_tax_amount_non_negative"),
        CheckConstraint("total_amount_gbp >= 0", name="ck_self_employed_invoices_total_non_negative"),
        Index("ix_self_employed_invoices_user_id_created_at", "user_id", "created_at"),
        Index("ix_self_employed_invoices_status", "status"),
        Index("ix_self_employed_invoices_due_date", "due_date"),
        Index("ix_self_employed_invoices_invoice_number", "invoice_number", unique=True),
        Index("ix_self_employed_invoices_recurring_plan_id", "recurring_plan_id"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    invoice_number = Column(String(length=32), nullable=False)
    customer_name = Column(String(length=180), nullable=False)
    customer_email = Column(String(length=255), nullable=True)
    customer_phone = Column(String(length=32), nullable=True)
    customer_address = Column(String(length=500), nullable=True)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    currency = Column(String(length=3), nullable=False, default="GBP")
    subtotal_gbp = Column(Float, nullable=False, default=0.0)
    tax_rate_percent = Column(Float, nullable=False, default=0.0)
    tax_amount_gbp = Column(Float, nullable=False, default=0.0)
    total_amount_gbp = Column(Float, nullable=False, default=0.0)
    payment_link_url = Column(String(length=500), nullable=True)
    payment_link_provider = Column(String(length=64), nullable=True)
    recurring_plan_id = Column(String, ForeignKey("self_employed_recurring_invoice_plans.id", ondelete="SET NULL"), nullable=True)
    brand_business_name = Column(String(length=180), nullable=True)
    brand_logo_url = Column(String(length=500), nullable=True)
    brand_accent_color = Column(String(length=16), nullable=True)
    reminder_last_sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(length=16), nullable=False, default="draft")
    notes = Column(String(length=1000), nullable=True)
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


class SelfEmployedInvoiceLine(Base):
    __tablename__ = "self_employed_invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_self_employed_invoice_lines_quantity_positive"),
        CheckConstraint("unit_price_gbp >= 0", name="ck_self_employed_invoice_lines_unit_price_non_negative"),
        CheckConstraint("line_total_gbp >= 0", name="ck_self_employed_invoice_lines_line_total_non_negative"),
        Index("ix_self_employed_invoice_lines_invoice_id", "invoice_id"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("self_employed_invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(length=500), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit_price_gbp = Column(Float, nullable=False, default=0.0)
    line_total_gbp = Column(Float, nullable=False, default=0.0)


class SelfEmployedInvoiceBrandProfile(Base):
    __tablename__ = "self_employed_invoice_brand_profiles"
    __table_args__ = (
        Index("ix_self_employed_invoice_brand_profiles_user_id", "user_id", unique=True),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    business_name = Column(String(length=180), nullable=False)
    logo_url = Column(String(length=500), nullable=True)
    accent_color = Column(String(length=16), nullable=True)
    payment_terms_note = Column(String(length=500), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class SelfEmployedRecurringInvoicePlan(Base):
    __tablename__ = "self_employed_recurring_invoice_plans"
    __table_args__ = (
        CheckConstraint("cadence IN ('weekly', 'monthly', 'quarterly')", name="ck_self_employed_recurring_invoice_plans_cadence"),
        CheckConstraint("tax_rate_percent >= 0 AND tax_rate_percent <= 100", name="ck_self_employed_recurring_invoice_plans_tax_rate"),
        Index("ix_self_employed_recurring_invoice_plans_user_id", "user_id"),
        Index("ix_self_employed_recurring_invoice_plans_next_issue_date", "next_issue_date"),
        Index("ix_self_employed_recurring_invoice_plans_active", "active"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    customer_name = Column(String(length=180), nullable=False)
    customer_email = Column(String(length=255), nullable=True)
    customer_phone = Column(String(length=32), nullable=True)
    customer_address = Column(String(length=500), nullable=True)
    currency = Column(String(length=3), nullable=False, default="GBP")
    tax_rate_percent = Column(Float, nullable=False, default=0.0)
    notes = Column(String(length=1000), nullable=True)
    line_items = Column(JSON, nullable=False)
    cadence = Column(String(length=16), nullable=False, default="monthly")
    next_issue_date = Column(Date, nullable=False)
    active = Column(Integer, nullable=False, default=1)
    last_generated_invoice_id = Column(String, nullable=True)
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


class SelfEmployedInvoiceReminder(Base):
    __tablename__ = "self_employed_invoice_reminders"
    __table_args__ = (
        CheckConstraint("reminder_type IN ('due_soon', 'overdue')", name="ck_self_employed_invoice_reminders_type"),
        CheckConstraint("channel IN ('email', 'sms', 'in_app')", name="ck_self_employed_invoice_reminders_channel"),
        CheckConstraint("status IN ('queued', 'sent', 'failed')", name="ck_self_employed_invoice_reminders_status"),
        Index("ix_self_employed_invoice_reminders_invoice_id", "invoice_id"),
        Index("ix_self_employed_invoice_reminders_user_id_created_at", "user_id", "created_at"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("self_employed_invoices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    reminder_type = Column(String(length=16), nullable=False)
    channel = Column(String(length=16), nullable=False, default="in_app")
    status = Column(String(length=16), nullable=False, default="sent")
    message = Column(String(length=500), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)


class SelfEmployedCalendarEvent(Base):
    __tablename__ = "self_employed_calendar_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled')",
            name="ck_self_employed_calendar_events_status",
        ),
        CheckConstraint(
            "notify_before_minutes >= 0 AND notify_before_minutes <= 10080",
            name="ck_self_employed_calendar_events_notify_before_minutes",
        ),
        CheckConstraint("notify_in_app IN (0, 1)", name="ck_self_employed_calendar_events_notify_in_app"),
        CheckConstraint("notify_email IN (0, 1)", name="ck_self_employed_calendar_events_notify_email"),
        CheckConstraint("notify_sms IN (0, 1)", name="ck_self_employed_calendar_events_notify_sms"),
        Index("ix_self_employed_calendar_events_user_starts_at", "user_id", "starts_at"),
        Index("ix_self_employed_calendar_events_status", "status"),
        Index("ix_self_employed_calendar_events_reminder_last_sent_at", "reminder_last_sent_at"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    title = Column(String(length=180), nullable=False)
    description = Column(String(length=1000), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    category = Column(String(length=64), nullable=False, default="general")
    recipient_name = Column(String(length=180), nullable=True)
    recipient_email = Column(String(length=255), nullable=True)
    recipient_phone = Column(String(length=32), nullable=True)
    notify_in_app = Column(Integer, nullable=False, default=1)
    notify_email = Column(Integer, nullable=False, default=0)
    notify_sms = Column(Integer, nullable=False, default=0)
    notify_before_minutes = Column(Integer, nullable=False, default=1440)
    reminder_last_sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(length=16), nullable=False, default="scheduled")
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


class SelfEmployedCalendarReminder(Base):
    __tablename__ = "self_employed_calendar_reminders"
    __table_args__ = (
        CheckConstraint(
            "reminder_type IN ('upcoming', 'overdue')",
            name="ck_self_employed_calendar_reminders_type",
        ),
        CheckConstraint(
            "channel IN ('email', 'sms', 'in_app')",
            name="ck_self_employed_calendar_reminders_channel",
        ),
        CheckConstraint(
            "status IN ('queued', 'sent', 'failed')",
            name="ck_self_employed_calendar_reminders_status",
        ),
        Index("ix_self_employed_calendar_reminders_event_id", "event_id"),
        Index("ix_self_employed_calendar_reminders_user_id_created_at", "user_id", "created_at"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(
        String,
        ForeignKey("self_employed_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String, nullable=False, index=True)
    reminder_type = Column(String(length=16), nullable=False)
    channel = Column(String(length=16), nullable=False, default="in_app")
    status = Column(String(length=16), nullable=False, default="sent")
    message = Column(String(length=500), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)


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


class MarketingSpendEntry(Base):
    __tablename__ = "marketing_spend_entries"
    __table_args__ = (
        CheckConstraint("spend_gbp >= 0", name="ck_marketing_spend_entries_spend_non_negative"),
        CheckConstraint("acquired_customers >= 0", name="ck_marketing_spend_entries_acquired_customers_non_negative"),
        Index("ix_marketing_spend_entries_month_start", "month_start"),
        Index("ix_marketing_spend_entries_channel", "channel"),
    )

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    month_start = Column(Date, nullable=False)
    channel = Column(String(length=64), nullable=False)
    spend_gbp = Column(Float, nullable=False, default=0.0)
    acquired_customers = Column(Integer, nullable=False, default=0)
    created_by_user_id = Column(String, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        index=True,
    )

