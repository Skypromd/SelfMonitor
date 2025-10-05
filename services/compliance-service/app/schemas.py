from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import datetime

class AuditEventCreate(BaseModel):
    user_id: str
    action: str
    details: Optional[Dict[str, Any]] = None

class AuditEvent(AuditEventCreate):
    id: uuid.UUID
    timestamp: datetime.datetime

    class Config:
        orm_mode = True
