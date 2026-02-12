import uuid
from typing import List

from pydantic import BaseModel, HttpUrl


class Partner(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    services_offered: List[str]
    website: HttpUrl

    class Config:
        orm_mode = True

