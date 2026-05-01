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

import httpx

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

    async def get_access_token(self, user_auth_code: str) -> str:
        """
        Exchange authorisation code for OAuth2 access token.
        Called once per user during the MTD authorisation flow.
        """
        async with httpx.AsyncClient() as client:
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
            self._access_token = data["access_token"]
            token: str = self._access_token or ""
            return token

    # ── period summaries (quarterly submission) ───────────────────────────────

    async def submit_period_summary(  # pylint: disable=too-many-positional-arguments
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
        payload = {
            "periodDates": {
                "periodStartDate": period_start,
                "periodEndDate":   period_end,
            },
            "periodIncome": {
                "turnover": round(income, 2),
                "other":    0.0,
            },
            "periodExpenses": {
                "costOfGoods":       0.0,
                "allowableExpenses": round(expenses, 2),
            },
        }

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
