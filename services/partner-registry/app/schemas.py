import datetime
import uuid
from enum import Enum
from typing import List, Literal, Optional

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


class SeedMRRPoint(BaseModel):
    month: str
    mrr_gbp: float


class SeedReadinessResponse(BaseModel):
    generated_at: datetime.datetime
    period_months: int
    current_month_mrr_gbp: float
    previous_month_mrr_gbp: float
    mrr_growth_percent: float
    rolling_3_month_avg_mrr_gbp: float
    paid_invoice_rate_percent: float
    active_invoice_count: int
    leads_last_90d: int
    qualified_last_90d: int
    converted_last_90d: int
    qualification_rate_percent: float
    conversion_rate_percent: float
    readiness_score_percent: float
    readiness_band: Literal["early", "progressing", "investable"]
    next_actions: List[str]
    monthly_mrr_series: List[SeedMRRPoint]


class PMFMonthlyCohortPoint(BaseModel):
    cohort_month: str
    new_users: int
    activated_users: int
    activation_rate_percent: float
    eligible_users_30d: int
    retained_users_30d: int
    retention_rate_30d_percent: float
    eligible_users_60d: int
    retained_users_60d: int
    retention_rate_60d_percent: float
    eligible_users_90d: int
    retained_users_90d: int
    retention_rate_90d_percent: float


class PMFEvidenceResponse(BaseModel):
    generated_at: datetime.datetime
    as_of_date: datetime.date
    cohort_months: int
    activation_window_days: int
    total_new_users: int
    activated_users: int
    activation_rate_percent: float
    eligible_users_30d: int
    retained_users_30d: int
    retention_rate_30d_percent: float
    eligible_users_60d: int
    retained_users_60d: int
    retention_rate_60d_percent: float
    eligible_users_90d: int
    retained_users_90d: int
    retention_rate_90d_percent: float
    pmf_band: Literal["early", "emerging", "pmf_confirmed"]
    notes: List[str]
    monthly_cohorts: List[PMFMonthlyCohortPoint]


class PMFGateStatusResponse(BaseModel):
    generated_at: datetime.datetime
    gate_name: Literal["seed_pmf_gate_v1"]
    activation_rate_percent: float
    retention_rate_90d_percent: float
    overall_nps_score: float
    eligible_users_90d: int
    total_nps_responses: int
    required_activation_rate_percent: float
    required_retention_rate_90d_percent: float
    required_overall_nps_score: float
    required_min_eligible_users_90d: int
    required_min_nps_responses: int
    activation_passed: bool
    retention_passed: bool
    nps_passed: bool
    sample_size_passed: bool
    gate_passed: bool
    summary: str
    next_actions: List[str]


class InvestorSnapshotExportResponse(BaseModel):
    generated_at: datetime.datetime
    as_of_date: datetime.date
    seed_readiness: SeedReadinessResponse
    pmf_evidence: PMFEvidenceResponse
    nps_trend: "NPSTrendResponse"
    pmf_gate: PMFGateStatusResponse


class NPSSubmissionRequest(BaseModel):
    score: int = Field(ge=0, le=10)
    feedback: Optional[str] = Field(default=None, max_length=1000)
    context_tag: Optional[str] = Field(default="dashboard", max_length=64)
    locale: Optional[str] = Field(default=None, max_length=16)


class NPSSubmissionResponse(BaseModel):
    response_id: uuid.UUID
    score_band: Literal["promoter", "passive", "detractor"]
    submitted_at: datetime.datetime
    message: str


class NPSMonthlyTrendPoint(BaseModel):
    month: str
    responses_count: int
    promoters_count: int
    passives_count: int
    detractors_count: int
    nps_score: float


class NPSTrendResponse(BaseModel):
    generated_at: datetime.datetime
    period_months: int
    total_responses: int
    promoters_count: int
    passives_count: int
    detractors_count: int
    overall_nps_score: float
    monthly_trend: List[NPSMonthlyTrendPoint]
    note: str


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

