import datetime
import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LeadStatus(str, Enum):
    initiated = "initiated"
    qualified = "qualified"
    rejected = "rejected"
    converted = "converted"


class BillingInvoiceStatus(str, Enum):
    generated = "generated"
    issued = "issued"
    paid = "paid"
    void = "void"


class Partner(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    services_offered: List[str]
    website: HttpUrl
    qualified_lead_fee_gbp: float
    converted_lead_fee_gbp: float

    model_config = ConfigDict(from_attributes=True)


class HandoffResponse(BaseModel):
    message: str
    lead_id: uuid.UUID
    audit_event_id: Optional[str] = None
    duplicated: bool = False


class LeadReportByPartner(BaseModel):
    partner_id: uuid.UUID
    partner_name: str
    leads_count: int
    unique_users: int


class LeadReportResponse(BaseModel):
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None
    total_leads: int
    unique_users: int
    by_partner: List[LeadReportByPartner]


class LeadStatusUpdateRequest(BaseModel):
    status: LeadStatus


class LeadStatusUpdateResponse(BaseModel):
    lead_id: uuid.UUID
    status: LeadStatus
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BillingReportByPartner(BaseModel):
    partner_id: uuid.UUID
    partner_name: str
    qualified_leads: int
    converted_leads: int
    unique_users: int
    qualified_lead_fee_gbp: float
    converted_lead_fee_gbp: float
    amount_gbp: float


class BillingReportResponse(BaseModel):
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None
    currency: str
    total_leads: int
    qualified_leads: int
    converted_leads: int
    unique_users: int
    total_amount_gbp: float
    by_partner: List[BillingReportByPartner]


class LeadFunnelSummaryResponse(BaseModel):
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None
    total_leads: int
    qualified_leads: int
    converted_leads: int
    qualification_rate_percent: float
    conversion_rate_from_qualified_percent: float
    overall_conversion_rate_percent: float


class PartnerPricingUpdateRequest(BaseModel):
    qualified_lead_fee_gbp: float = Field(ge=0)
    converted_lead_fee_gbp: float = Field(ge=0)


class LeadListItem(BaseModel):
    id: uuid.UUID
    user_id: str
    partner_id: uuid.UUID
    partner_name: str
    status: LeadStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime


class LeadListResponse(BaseModel):
    total: int
    items: List[LeadListItem]


class BillingInvoiceGenerateRequest(BaseModel):
    partner_id: Optional[uuid.UUID] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    statuses: Optional[List[LeadStatus]] = None


class BillingInvoiceLine(BaseModel):
    partner_id: uuid.UUID
    partner_name: str
    qualified_leads: int
    converted_leads: int
    unique_users: int
    qualified_lead_fee_gbp: float
    converted_lead_fee_gbp: float
    amount_gbp: float


class BillingInvoiceSummary(BaseModel):
    id: uuid.UUID
    invoice_number: str
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None
    due_date: datetime.date
    currency: str
    status: BillingInvoiceStatus
    total_amount_gbp: float
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BillingInvoiceDetail(BillingInvoiceSummary):
    generated_by_user_id: str
    partner_id: Optional[uuid.UUID] = None
    statuses: List[LeadStatus]
    updated_at: datetime.datetime
    lines: List[BillingInvoiceLine]


class BillingInvoiceListResponse(BaseModel):
    total: int
    items: List[BillingInvoiceSummary]


class BillingInvoiceStatusUpdateRequest(BaseModel):
    status: BillingInvoiceStatus

