from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
import uuid
import datetime

class ExtractedData(BaseModel):
    total_amount: Optional[float] = None
    vendor_name: Optional[str] = None
    transaction_date: Optional[datetime.date] = None
    suggested_category: Optional[str] = None
    expense_article: Optional[str] = None
    is_potentially_deductible: Optional[bool] = None
    ocr_provider: Optional[str] = None
    raw_text_excerpt: Optional[str] = None
    receipt_draft_transaction_id: Optional[str] = None
    receipt_draft_duplicated: Optional[bool] = None

class DocumentBase(BaseModel):
    filename: str
    filepath: str
    status: Literal['processing', 'completed', 'failed'] = 'processing'

class Document(DocumentBase):
    id: uuid.UUID
    user_id: str
    uploaded_at: datetime.datetime
    extracted_data: Optional[ExtractedData] = None

    model_config = ConfigDict(from_attributes=True)
