"""Stable audit action names for compliance-service and internal logs (variant B)."""

from enum import StrEnum


class CISAuditAction(StrEnum):
    CIS_SUSPECTED_FROM_BANK_TRANSACTION = "cis_suspected_from_bank_transaction"
    CIS_CLASSIFIED_CONFIRMED = "cis_classified_confirmed"
    CIS_CLASSIFIED_NOT_CIS = "cis_classified_not_cis"
    CIS_STATEMENT_UPLOADED = "cis_statement_uploaded"
    CIS_STATEMENT_EXTRACTION_COMPLETED = "cis_statement_extraction_completed"
    CIS_ATTESTATION_ACCEPTED_NO_STATEMENT = "cis_attestation_accepted_no_statement"
    CIS_AMOUNTS_SAVED = "cis_amounts_saved"
    CIS_UNVERIFIED_SUBMIT_CONFIRMED = "cis_unverified_submit_confirmed"
    CIS_RECORD_UPDATED = "cis_record_updated"
    CIS_EVIDENCE_PACK_SHARED_DOWNLOAD = "cis_evidence_pack_shared_download"
