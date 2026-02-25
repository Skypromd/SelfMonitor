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
    reconciliation_status: Optional[str] = None
    ignored_candidate_ids: Optional[List[str]] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionImportRequest(BaseModel):
    account_id: uuid.UUID
    transactions: List[TransactionBase]


class TransactionImportResponse(BaseModel):
    message: str
    imported_count: int
    created_count: int
    reconciled_receipt_drafts: int
    skipped_duplicates: int


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


class ReceiptDraftCandidate(BaseModel):
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    provider_transaction_id: str
    date: datetime.date
    description: str
    amount: float
    currency: str
    category: Optional[str] = None
    confidence_score: float
    ignored: bool = False


class UnmatchedReceiptDraftItem(BaseModel):
    draft_transaction: Transaction
    candidates: List[ReceiptDraftCandidate]


class UnmatchedReceiptDraftsResponse(BaseModel):
    total: int
    items: List[UnmatchedReceiptDraftItem]


class ReceiptDraftManualReconcileRequest(BaseModel):
    target_transaction_id: uuid.UUID


class ReceiptDraftManualReconcileResponse(BaseModel):
    reconciled_transaction: Transaction
    removed_transaction_id: uuid.UUID


class ReceiptDraftCandidatesResponse(BaseModel):
    draft_transaction: Transaction
    total: int
    items: List[ReceiptDraftCandidate]


class ReceiptDraftIgnoreCandidateRequest(BaseModel):
    target_transaction_id: uuid.UUID


class ReceiptDraftStateUpdateResponse(BaseModel):
    draft_transaction: Transaction
