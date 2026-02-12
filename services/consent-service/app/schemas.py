import datetime
import uuid
from typing import List, Literal

from pydantic import BaseModel


class ConsentCreate(BaseModel):
    connection_id: uuid.UUID
    provider: str
    scopes: List[str]


class Consent(BaseModel):
    id: uuid.UUID
    user_id: str
    connection_id: uuid.UUID
    status: Literal["active", "revoked"]
    provider: str
    scopes: List[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True

