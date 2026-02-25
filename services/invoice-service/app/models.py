from sqlalchemy import Column, String, DateTime, Numeric, Integer, Boolean, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from .database import Base

class Invoice(Base):
    """Core invoice model for business invoicing"""
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Business owner
    company_id = Column(String, nullable=True, index=True)  # Multi-company support
    
    # Client Information
    client_name = Column(String, nullable=False)
    client_email = Column(String, nullable=True)
    client_address = Column(Text, nullable=True)
    client_vat_number = Column(String, nullable=True)
    
    # Invoice Details
    issue_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=False)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    
    # Financial Information
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    vat_rate = Column(Numeric(5, 2), nullable=False, default=20.0)  # UK VAT 20%
    vat_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Status & Metadata
    status = Column(String, nullable=False, default='draft')  # draft, sent, paid, overdue, cancelled
    currency = Column(String(3), nullable=False, default='GBP')
    notes = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    
    # File Storage
    pdf_file_path = Column(String, nullable=True)
    
    # Audit Trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("InvoicePayment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    """Individual line items within an invoice"""
    __tablename__ = "invoice_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    
    # Item Details
    description = Column(String, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)
    
    # Tax Information
    vat_rate = Column(Numeric(5, 2), nullable=False, default=20.0)
    vat_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Product/Service categorization
    category = Column(String, nullable=True)  # For expense categorization
    product_code = Column(String, nullable=True)
    
    # Relationship
    invoice = relationship("Invoice", back_populates="line_items")


class InvoicePayment(Base):
    """Payment records for invoices"""
    __tablename__ = "invoice_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    
    # Payment Details
    payment_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String, nullable=False)  # bank_transfer, card, cash, etc.
    reference_number = Column(String, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    invoice = relationship("Invoice", back_populates="payments")


class InvoiceTemplate(Base):
    """Customizable invoice templates for businesses"""
    __tablename__ = "invoice_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    company_id = Column(String, nullable=True, index=True)
    
    # Template Details
    template_name = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)
    
    # Company Information
    company_name = Column(String, nullable=False)
    company_address = Column(Text, nullable=True)
    company_email = Column(String, nullable=True)
    company_phone = Column(String, nullable=True)
    company_website = Column(String, nullable=True)
    company_logo_url = Column(String, nullable=True)
    vat_registration_number = Column(String, nullable=True)
    companies_house_number = Column(String, nullable=True)
    
    # Invoice Configuration
    default_vat_rate = Column(Numeric(5, 2), nullable=False, default=20.0)
    default_currency = Column(String(3), nullable=False, default='GBP')
    payment_terms_days = Column(Integer, nullable=False, default=30)
    
    # Template Styling
    color_scheme = Column(JSON, nullable=True)  # Colors for PDF templates
    font_settings = Column(JSON, nullable=True)  # Font preferences
    
    # Standard Text
    default_terms = Column(Text, nullable=True)
    default_notes = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RecurringInvoice(Base):
    """Recurring invoice configuration"""
    __tablename__ = "recurring_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("invoice_templates.id"), nullable=False)
    
    # Client Information
    client_name = Column(String, nullable=False)
    client_email = Column(String, nullable=True)
    client_address = Column(Text, nullable=True)
    
    # Recurrence Settings
    frequency = Column(String, nullable=False)  # weekly, monthly, quarterly, annually
    next_issue_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Invoice Settings
    invoice_template = Column(JSON, nullable=False)  # Stored invoice structure
    auto_send = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    template = relationship("InvoiceTemplate")