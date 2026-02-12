import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


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

