"""
Type stubs for invoice service app module
"""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel

class InvoiceLineItemCreate(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    category: Optional[str]
    product_code: Optional[str]

class InvoiceCreate(BaseModel):
    client_name: str
    line_items: List[InvoiceLineItemCreate] 
    due_date: datetime
    client_email: Optional[str]
    client_address: Optional[str]
    client_vat_number: Optional[str]
    vat_rate: Decimal
    currency: str
    notes: Optional[str]
    terms_conditions: Optional[str]
    company_id: Optional[str]
    template_id: Optional[str]

class CalculatedLineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    line_total: Decimal
    vat_amount: Decimal
    category: Optional[str]
    product_code: Optional[str]

class CalculatedInvoice(BaseModel):
    client_name: str
    client_email: Optional[str]
    client_address: Optional[str]
    client_vat_number: Optional[str]
    due_date: datetime
    vat_rate: Decimal
    currency: str
    notes: Optional[str]
    terms_conditions: Optional[str]
    company_id: Optional[str]
    template_id: Optional[str]
    line_items: List[CalculatedLineItem]
    subtotal: Decimal
    total_vat: Decimal
    total_amount: Decimal
    discount_amount: Decimal

class schemas:
    InvoiceCreate = InvoiceCreate
    InvoiceLineItemCreate = InvoiceLineItemCreate
    CalculatedInvoice = CalculatedInvoice
    CalculatedLineItem = CalculatedLineItem

class InvoiceCalculator:
    def calculate_totals(self, invoice_data: InvoiceCreate) -> CalculatedInvoice: ...