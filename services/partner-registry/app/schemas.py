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

