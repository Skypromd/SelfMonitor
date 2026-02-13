from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
import uuid
import datetime

class TransactionBase(BaseModel):
    provider_transaction_id: str
    date: datetime.date
    description: str
    amount: float
    currency: str

class Transaction(TransactionBase):
    id: uuid.UUID
    account_id: uuid.UUID
    user_id: str
    category: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionImportRequest(BaseModel):
    account_id: uuid.UUID
    transactions: List[TransactionBase]

class TransactionUpdateRequest(BaseModel):
    category: str


class ReceiptDraftCreateRequest(BaseModel):
    document_id: uuid.UUID
    filename: str
    transaction_date: datetime.date
    total_amount: float = Field(gt=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    vendor_name: Optional[str] = None
    suggested_category: Optional[str] = None
    expense_article: Optional[str] = None
    is_potentially_deductible: Optional[bool] = None


class ReceiptDraftCreateResponse(BaseModel):
    transaction: Transaction
    duplicated: bool
