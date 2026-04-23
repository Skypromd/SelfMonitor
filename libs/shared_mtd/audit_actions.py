"""Stable audit action names for MTD flows forwarded to compliance-service."""

from enum import StrEnum


class MTDAuditAction(StrEnum):
    MTD_QUARTERLY_SUBMITTED = "mtd_quarterly_submitted"
    MTD_FINAL_DECLARATION_SUBMITTED = "mtd_final_declaration_submitted"
