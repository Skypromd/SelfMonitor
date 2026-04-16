"""
HMRC MTD API client stub.

In production this would call:
  https://api.service.hmrc.gov.uk/individuals/self-assessment/income-tax/...

Currently implements OAuth2 token management and request signing stubs.
Replace HMRC_BASE_URL with the sandbox URL for testing:
  https://test-api.service.hmrc.gov.uk
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from libs.shared_mtd import build_mtd_self_employment_period_summary

log = logging.getLogger(__name__)

HMRC_BASE_URL     = os.getenv("HMRC_BASE_URL", "https://test-api.service.hmrc.gov.uk")
HMRC_CLIENT_ID    = os.getenv("HMRC_CLIENT_ID", "")
HMRC_CLIENT_SECRET = os.getenv("HMRC_CLIENT_SECRET", "")


class HMRCClient:
    """
    Thin async client for HMRC MTD Income Tax Self Assessment API.

    API reference:
      https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-income-received-api
    """

    def __init__(self) -> None:
        self._base = HMRC_BASE_URL.rstrip("/")
        self._access_token: str | None = None

    # ── auth ─────────────────────────────────────────────────────────────────

    async def exchange_authorization_code(
        self, user_auth_code: str
    ) -> tuple[str, int | None]:
        """
        Exchange authorisation code for OAuth2 access token.
        Returns (access_token, expires_in_seconds) per HMRC token response.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}/oauth/token",
                data={
                    "grant_type":    "authorization_code",
                    "code":          user_auth_code,
                    "client_id":     HMRC_CLIENT_ID,
                    "client_secret": HMRC_CLIENT_SECRET,
                    "redirect_uri":  os.getenv("HMRC_REDIRECT_URI", "http://localhost:8022/hmrc/callback"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token = data["access_token"]
            raw_exp = data.get("expires_in")
            expires_in: int | None
            try:
                expires_in = int(raw_exp) if raw_exp is not None else None
            except (TypeError, ValueError):
                expires_in = None
            self._access_token = token
            return token, expires_in

    async def get_access_token(self, user_auth_code: str) -> str:
        token, _ = await self.exchange_authorization_code(user_auth_code)
        return token

    # ── period summaries (quarterly submission) ───────────────────────────────

    async def submit_period_summary(
        self,
        nino: str,
        tax_year: str,          # "2026-27"
        period_start: str,      # "2026-04-06"
        period_end: str,        # "2026-07-05"
        income: float,
        expenses: float,
        access_token: str,
    ) -> dict:
        """
        POST /individuals/income-received/self-employment/{nino}/{taxYear}

        Returns HMRC submission receipt with transactionReference.
        """
        payload = build_mtd_self_employment_period_summary(
            period_start_iso=period_start,
            period_end_iso=period_end,
            turnover=income,
            allowable_expenses=expenses,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}/individuals/income-received/self-employment/{nino}/{tax_year}",
                json=payload,
                headers={
                    "Authorization":  f"Bearer {access_token}",
                    "Accept":         "application/vnd.hmrc.3.0+json",
                    "Content-Type":   "application/json",
                },
            )
            resp.raise_for_status()
            log.info("HMRC submission OK: %s %s", nino, tax_year)
            return resp.json()

    async def get_submission_status(
        self, nino: str, tax_year: str, access_token: str
    ) -> dict:
        """Retrieve previously submitted period summaries."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self._base}/individuals/income-received/self-employment/{nino}/{tax_year}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept":        "application/vnd.hmrc.3.0+json",
                },
            )
            resp.raise_for_status()
            return resp.json()
