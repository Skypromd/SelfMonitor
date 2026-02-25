from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent" 
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    PARTIALLY_PAID = "partially_paid"

class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    CHEQUE = "cheque"
    PAYPAL = "paypal"
    STRIPE = "stripe"

class RecurrenceFrequency(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"

# === LINE ITEM SCHEMAS ===
class InvoiceLineItemBase(BaseModel):
    description: str = Field(..., max_length=500, description="Item description")
    quantity: Decimal = Field(default=1, ge=0, description="Quantity")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    vat_rate: Decimal = Field(default=20.0, ge=0, le=100, description="VAT rate percentage")
    category: Optional[str] = Field(None, max_length=100)
    product_code: Optional[str] = Field(None, max_length=50)

class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass

class InvoiceLineItemUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    category: Optional[str] = Field(None, max_length=100)
    product_code: Optional[str] = Field(None, max_length=50)

class InvoiceLineItem(InvoiceLineItemBase):
    id: str
    line_total: Decimal
    vat_amount: Decimal
    
    class Config:
        from_attributes = True

# === PAYMENT SCHEMAS ===
class InvoicePaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    payment_date: datetime = Field(default_factory=datetime.utcnow)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)

class InvoicePaymentCreate(InvoicePaymentBase):
    pass

class InvoicePayment(InvoicePaymentBase):
    id: str
    invoice_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# === INVOICE SCHEMAS ===
class InvoiceBase(BaseModel):
    client_name: str = Field(..., max_length=200, description="Client company name")
    client_email: Optional[EmailStr] = Field(None, description="Client email")
    client_address: Optional[str] = Field(None, max_length=1000)
    client_vat_number: Optional[str] = Field(None, max_length=50)
    
    due_date: datetime = Field(..., description="Payment due date")
    
    vat_rate: Decimal = Field(default=20.0, ge=0, le=100, description="Default VAT rate")
    currency: str = Field(default="GBP", max_length=3, description="Invoice currency")
    
    notes: Optional[str] = Field(None, max_length=2000)
    terms_conditions: Optional[str] = Field(None, max_length=5000)

class InvoiceCreate(InvoiceBase):
    company_id: Optional[str] = Field(None, description="Company ID for multi-company")
    line_items: List[InvoiceLineItemCreate] = Field(..., min_items=1, description="Invoice line items")
    template_id: Optional[str] = Field(None, description="Invoice template to use")

class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = Field(None, max_length=200)
    client_email: Optional[EmailStr] = None
    client_address: Optional[str] = Field(None, max_length=1000)
    client_vat_number: Optional[str] = Field(None, max_length=50)
    
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None
    
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    currency: Optional[str] = Field(None, max_length=3)
    
    notes: Optional[str] = Field(None, max_length=2000)
    terms_conditions: Optional[str] = Field(None, max_length=5000)

class Invoice(InvoiceBase):
    id: str
    invoice_number: str
    user_id: str
    company_id: Optional[str]
    
    issue_date: datetime
    payment_date: Optional[datetime]
    
    subtotal: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    
    status: InvoiceStatus
    pdf_file_path: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    line_items: List[InvoiceLineItem] = []
    payments: List[InvoicePayment] = []
    
    class Config:
        from_attributes = True

# === TEMPLATE SCHEMAS ===
class InvoiceTemplateBase(BaseModel):
    template_name: str = Field(..., max_length=100, description="Template name")
    company_name: str = Field(..., max_length=200, description="Company name")
    company_address: Optional[str] = Field(None, max_length=1000)
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = Field(None, max_length=50)
    company_website: Optional[str] = Field(None, max_length=200)
    company_logo_url: Optional[str] = Field(None, max_length=500)
    vat_registration_number: Optional[str] = Field(None, max_length=50)
    companies_house_number: Optional[str] = Field(None, max_length=50)
    
    default_vat_rate: Decimal = Field(default=20.0, ge=0, le=100)
    default_currency: str = Field(default="GBP", max_length=3)
    payment_terms_days: int = Field(default=30, ge=1, le=365)
    
    default_terms: Optional[str] = Field(None, max_length=5000)
    default_notes: Optional[str] = Field(None, max_length=2000)
    
    color_scheme: Optional[dict] = Field(None, description="Color scheme for PDF")
    font_settings: Optional[dict] = Field(None, description="Font preferences")

class InvoiceTemplateCreate(InvoiceTemplateBase):
    company_id: Optional[str] = Field(None, description="Company ID")
    is_default: bool = Field(default=False)

class InvoiceTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    company_address: Optional[str] = Field(None, max_length=1000)
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = Field(None, max_length=50)
    company_website: Optional[str] = Field(None, max_length=200)
    is_default: Optional[bool] = None
    default_vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    payment_terms_days: Optional[int] = Field(None, ge=1, le=365)

class InvoiceTemplate(InvoiceTemplateBase):
    id: str
    user_id: str
    company_id: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# === RECURRING INVOICE SCHEMAS ===
class RecurringInvoiceBase(BaseModel):
    client_name: str = Field(..., max_length=200)
    client_email: Optional[EmailStr] = None
    client_address: Optional[str] = Field(None, max_length=1000)
    frequency: RecurrenceFrequency = Field(..., description="Recurrence frequency")
    next_issue_date: datetime = Field(..., description="Next invoice date")
    end_date: Optional[datetime] = Field(None, description="End date for recurrence")
    auto_send: bool = Field(default=False, description="Auto-send invoices")

class RecurringInvoiceCreate(RecurringInvoiceBase):
    template_id: str = Field(..., description="Invoice template ID")
    invoice_template: dict = Field(..., description="Invoice template data")

class RecurringInvoice(RecurringInvoiceBase):
    id: str
    user_id: str
    template_id: str
    is_active: bool
    created_at: datetime
    template: Optional[InvoiceTemplate] = None
    
    class Config:
        from_attributes = True

# === REPORTING SCHEMAS ===
class InvoiceReportFilters(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[List[InvoiceStatus]] = None
    client_name: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    company_id: Optional[str] = None

class InvoiceStats(BaseModel):
    total_invoices: int
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    overdue_amount: Decimal
    average_payment_time: Optional[float]  # Days
    
class InvoiceReportSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    stats: InvoiceStats
    invoices_by_status: dict
    monthly_breakdown: List[dict]
    top_clients: List[dict]

# === PDF GENERATION SCHEMAS ===
class PDFGenerationRequest(BaseModel):
    invoice_id: str
    template_id: Optional[str] = None
    custom_styling: Optional[dict] = None
    
class PDFGenerationResponse(BaseModel):
    pdf_url: str
    file_path: str
    generated_at: datetime