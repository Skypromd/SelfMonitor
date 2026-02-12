import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, HttpUrl


class Partner(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    services_offered: List[str]
    website: HttpUrl

    model_config = ConfigDict(from_attributes=True)

