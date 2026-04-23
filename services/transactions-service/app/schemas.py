import datetime
import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    business_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    reconciliation_status: Optional[str] = None
    ignored_candidate_ids: Optional[List[str]] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class UserBusinessOut(BaseModel):
    id: uuid.UUID
    user_id: str
    display_name: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UserBusinessCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class UserBusinessRename(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


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
    category: Optional[str] = None
    tax_category: Optional[str] = None
    business_use_percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )


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
    vat_amount_gbp: Optional[float] = Field(default=None, ge=0)


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


class ReceiptDraftUpdateRequest(BaseModel):
    total_amount: Optional[float] = Field(default=None, gt=0)
    vendor_name: Optional[str] = None
    transaction_date: Optional[datetime.date] = None
    suggested_category: Optional[str] = None
    vat_amount_gbp: Optional[float] = Field(default=None, ge=0)


# --- CIS variant B + accountant ---


class CISAttestationIn(BaseModel):
    attestation_version: str = Field(min_length=1, max_length=64)
    attestation_text: str = Field(min_length=1, max_length=20000)
    client_context: dict[str, Any] = Field(default_factory=dict)


class CISRecordCreate(BaseModel):
    contractor_name: str = Field(min_length=1, max_length=300)
    period_start: datetime.date
    period_end: datetime.date
    gross_total: float = Field(ge=0)
    materials_total: float = Field(default=0.0, ge=0)
    cis_deducted_total: float = Field(ge=0)
    net_paid_total: float
    evidence_status: str = Field(min_length=1, max_length=64)
    document_id: Optional[str] = Field(default=None, max_length=128)
    source: str = Field(min_length=1, max_length=64)
    matched_bank_transaction_ids: Optional[List[str]] = None
    attestation: Optional[CISAttestationIn] = None
    report_status: str = Field(default="draft", max_length=64)


class CISRecordOut(BaseModel):
    id: uuid.UUID
    user_id: str
    contractor_name: str
    period_start: datetime.date
    period_end: datetime.date
    gross_total: float
    materials_total: float
    cis_deducted_total: float
    net_paid_total: float
    evidence_status: str
    document_id: Optional[str]
    source: str
    matched_bank_transaction_ids: Optional[List[str]]
    attestation_json: Optional[dict[str, Any]]
    report_status: str
    reconciliation_status: Optional[str] = None
    bank_net_observed_gbp: Optional[float] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class CISObligationOut(BaseModel):
    id: uuid.UUID
    user_id: str
    cis_tax_month_label: str
    contractor_key: str
    status: str
    snooze_until: Optional[datetime.date] = None
    last_reminded_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class CISReviewTaskOut(BaseModel):
    id: uuid.UUID
    user_id: str
    status: str
    suspected_transaction_id: Optional[uuid.UUID]
    cis_record_id: Optional[uuid.UUID]
    payer_label: Optional[str]
    suspect_reason: Optional[str]
    next_reminder_at: Optional[datetime.date]
    reminder_meta: Optional[dict[str, Any]] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class CISSuspectTaskCreate(BaseModel):
    transaction_id: uuid.UUID
    reason: str = Field(default="manual_flag", max_length=500)


class CISReviewTaskPatch(BaseModel):
    status: str = Field(min_length=1, max_length=64)
    cis_record_id: Optional[uuid.UUID] = None
    payer_label: Optional[str] = Field(default=None, max_length=300)


class CISRecordPatch(BaseModel):
    contractor_name: Optional[str] = Field(default=None, max_length=300)
    report_status: Optional[str] = Field(default=None, max_length=64)
    document_id: Optional[str] = Field(default=None, max_length=128)
    evidence_status: Optional[str] = Field(default=None, max_length=64)


class AccountantDelegationCreate(BaseModel):
    accountant_user_id: str = Field(min_length=1, max_length=200)
    scopes: List[str] = Field(default_factory=list)
    can_submit_hmrc: bool = False
    expires_at: Optional[datetime.datetime] = None


class AccountantDelegationOut(BaseModel):
    id: uuid.UUID
    client_user_id: str
    accountant_user_id: str
    scopes: List[str]
    can_submit_hmrc: bool
    expires_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    revoked_at: Optional[datetime.datetime]

    model_config = ConfigDict(from_attributes=True)


class EvidencePackManifestOut(BaseModel):
    manifest: dict[str, Any]


class EvidenceShareTokenOut(BaseModel):
    token: str
    expires_at: datetime.datetime
    relative_download_path: str = "/cis/evidence-pack/shared-zip"
