from pydantic import BaseModel
from typing import Optional, Literal
import uuid
import datetime

class ExtractedData(BaseModel):
    total_amount: Optional[float] = None
    vendor_name: Optional[str] = None
    transaction_date: Optional[datetime.date] = None

class DocumentBase(BaseModel):
    filename: str
    filepath: str
    status: Literal['processing', 'completed', 'failed'] = 'processing'

class Document(DocumentBase):
    id: uuid.UUID
    user_id: str
    uploaded_at: datetime.datetime
    extracted_data: Optional[ExtractedData] = None

    class Config:
        orm_mode = True
