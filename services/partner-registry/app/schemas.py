import datetime
import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class LeadStatus(str, Enum):
    initiated = "initiated"
    qualified = "qualified"
    rejected = "rejected"
    converted = "converted"


class Partner(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    services_offered: List[str]
    website: HttpUrl

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

