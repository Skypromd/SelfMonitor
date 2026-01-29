from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
import uuid
import datetime

class TransactionBase(BaseModel):
    provider_transaction_id: str
    date: datetime.date
    description: str
    amount: float
    currency: str
    tax_category: Optional[str] = None
    business_use_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Business-use percentage (0-100).",
    )

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
    category: Optional[str] = None
    tax_category: Optional[str] = None
    business_use_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Business-use percentage (0-100).",
    )


class PartnerIngestionRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    source_system: str
    user_reference: str
    account_id: uuid.UUID
    tax_year: Optional[str] = None
    transactions: List[TransactionBase]
    metadata: Optional[Dict[str, Any]] = None


class IngestionResult(BaseModel):
    message: str
    imported_count: int
    skipped_count: int
