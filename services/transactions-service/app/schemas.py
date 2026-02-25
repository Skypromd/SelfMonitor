from pydantic import BaseModel, ConfigDict
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
