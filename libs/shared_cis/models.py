"""Reference models for CIS records (persist in a dedicated service / DB — not wired here yet)."""

from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CISEvidenceStatus(StrEnum):
    VERIFIED_WITH_STATEMENT = "verified_with_statement"
    SELF_ATTESTED_NO_STATEMENT = "self_attested_no_statement"


class CISSource(StrEnum):
    OCR = "ocr"
    MANUAL_AFTER_UPLOAD = "manual_after_upload"
    MANUAL_ATTESTED = "manual_attested"


class CISAttestationRecord(BaseModel):
    attested_at: datetime.datetime
    attestation_version: str = Field(min_length=1, max_length=64)
    attestation_text: str = Field(min_length=1, max_length=20000)
    attested_by_user_id: str = Field(min_length=1, max_length=200)
    client_context: dict[str, Any] = Field(default_factory=dict)


class CISRecordBase(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    contractor_name: str = Field(min_length=1, max_length=300)
    period_start: datetime.date
    period_end: datetime.date
    gross_total: float = Field(ge=0)
    materials_total: float = Field(ge=0)
    cis_deducted_total: float = Field(ge=0)
    net_paid_total: float
    evidence_status: CISEvidenceStatus
    document_id: str | None = Field(default=None, max_length=128)
    source: CISSource
    matched_bank_transaction_ids: list[str] = Field(default_factory=list)
    attestation: CISAttestationRecord | None = None
