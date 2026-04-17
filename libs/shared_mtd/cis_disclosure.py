"""CIS credit disclosure embedded in MTD quarterly report (variant B: verified vs self-attested)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MTDQuarterlyCISDisclosure(BaseModel):
    """Mirrors tax-engine split; informational for audit and submit gating."""

    credit_verified_gbp: float = Field(0.0, ge=0, description="CIS deductions backed by uploaded statement.")
    credit_self_attested_unverified_gbp: float = Field(
        0.0,
        ge=0,
        description="CIS amounts without statement; user-attested UNVERIFIED.",
    )
