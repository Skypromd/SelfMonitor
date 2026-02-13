from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal
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
    ocr_confidence: Optional[float] = None
    needs_review: Optional[bool] = None
    review_reason: Optional[str] = None
    review_status: Optional[Literal["pending", "confirmed", "corrected", "ignored"]] = None
    reviewed_at: Optional[datetime.datetime] = None
    review_notes: Optional[str] = None
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


class DocumentReviewQueueResponse(BaseModel):
    total: int
    items: List[Document]


class DocumentReviewUpdateRequest(BaseModel):
    total_amount: Optional[float] = Field(default=None, gt=0)
    vendor_name: Optional[str] = None
    transaction_date: Optional[datetime.date] = None
    suggested_category: Optional[str] = None
    expense_article: Optional[str] = None
    is_potentially_deductible: Optional[bool] = None
    review_status: Literal["confirmed", "corrected", "ignored"] = "confirmed"
    review_notes: Optional[str] = None
