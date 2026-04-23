from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
import uuid
import datetime

class AuditEventCreate(BaseModel):
    user_id: str = Field(max_length=200)
    action: str = Field(max_length=200)
    details: Optional[Dict[str, Any]] = None

class AuditEvent(AuditEventCreate):
    id: uuid.UUID
    timestamp: datetime.datetime
    prev_chain_hash: Optional[str] = None
    chain_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
