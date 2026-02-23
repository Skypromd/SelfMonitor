import os
import uuid
from typing import Optional, Dict, Any, List

import httpx

from .base import BankingProvider, ProviderInitResult, ProviderCallbackResult


class SaltedgeProvider(BankingProvider):
    provider_id = "saltedge"
    display_name = "Salt Edge"

    def __init__(self) -> None:
        self.base_url = os.getenv("SALTEDGE_BASE_URL", "https://www.saltedge.com/api/v5")
        self.app_id = os.getenv("SALTEDGE_APP_ID")
        self.secret = os.getenv("SALTEDGE_SECRET")
        self.customer_prefix = os.getenv("SALTEDGE_CUSTOMER_PREFIX", "selfmonitor")
        scopes_env = os.getenv("SALTEDGE_SCOPES", "accounts,transactions")
        self.scopes = [scope.strip() for scope in scopes_env.split(",") if scope.strip()]

    def is_configured(self) -> bool:
        return bool(self.app_id and self.secret)

    def _headers(self) -> Dict[str, str]:
        return {
            "App-id": self.app_id or "",
            "Secret": self.secret or "",
            "Content-Type": "application/json",
        }

    async def initiate(self, user_id: str, redirect_uri: str) -> ProviderInitResult:
        if not self.is_configured():
            raise ValueError("Salt Edge credentials are not configured.")

        customer_id = await self._ensure_customer(user_id)
        connect_url = await self._create_connect_session(customer_id, redirect_uri)
        return ProviderInitResult(consent_url=connect_url)

    async def handle_callback(
        self,
        user_id: str,
        code: Optional[str] = None,
        connection_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> ProviderCallbackResult:
        if not connection_id:
            raise ValueError("connection_id is required for Salt Edge callbacks.")

        transactions = []
        if self.is_configured():
            transactions = await self._fetch_transactions(connection_id)

        return ProviderCallbackResult(
            connection_id=connection_id,
            status="connected",
            message="Salt Edge connection established.",
            transactions=transactions,
            metadata={
                "provider_id": self.provider_id,
                "connection_id": connection_id,
            },
        )

    async def _ensure_customer(self, user_id: str) -> str:
        external_id = f"{self.customer_prefix}-{user_id}"
        payload = {"data": {"identifier": external_id}}
        url = f"{self.base_url}/customers"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers(), timeout=10.0)
            if response.status_code in (200, 201):
                data = response.json().get("data", {})
                return str(data.get("id") or data.get("identifier") or external_id)
            if response.status_code == 409:
                return external_id
            raise ValueError(f"Salt Edge customer creation failed: {response.text}")

    async def _create_connect_session(self, customer_id: str, redirect_uri: str) -> str:
        url = f"{self.base_url}/connect_sessions/create"
        payload: Dict[str, Any] = {
            "data": {
                "customer_id": customer_id,
                "return_to": redirect_uri,
            }
        }
        if self.scopes:
            payload["data"]["consent"] = {
                "scopes": self.scopes,
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers(), timeout=10.0)
            if response.status_code not in (200, 201):
                raise ValueError(f"Salt Edge connect session failed: {response.text}")
            data = response.json().get("data", {})
            connect_url = data.get("connect_url") or data.get("url")
            if not connect_url:
                raise ValueError("Salt Edge connect session response missing connect URL.")
            return connect_url

    async def _fetch_transactions(self, connection_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/transactions"
        params = {"connection_id": connection_id}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=self._headers(), timeout=15.0)
            if response.status_code != 200:
                return []
            raw_transactions = response.json().get("data", [])

        mapped: List[Dict[str, Any]] = []
        for item in raw_transactions:
            provider_transaction_id = item.get("id") or item.get("transaction_id")
            date_value = item.get("made_on") or item.get("date")
            amount = item.get("amount")
            currency = item.get("currency_code") or item.get("currency")
            description = item.get("description") or item.get("merchant_name") or "Transaction"

            if not provider_transaction_id or not date_value or amount is None or not currency:
                continue

            mapped.append(
                {
                    "provider_transaction_id": str(provider_transaction_id),
                    "date": date_value,
                    "description": description,
                    "amount": float(amount),
                    "currency": currency,
                }
            )

        return mapped
