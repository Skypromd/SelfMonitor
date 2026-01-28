import uuid
import datetime
from typing import Optional

from .base import BankingProvider, ProviderInitResult, ProviderCallbackResult


class MockProvider(BankingProvider):
    provider_id = "mock_bank"
    display_name = "Mock Bank"

    async def initiate(self, user_id: str, redirect_uri: str) -> ProviderInitResult:
        consent_url = (
            "https://fake-bank-provider.com/consent"
            f"?client_id={self.provider_id}&redirect_uri={redirect_uri}&scope=transactions"
        )
        return ProviderInitResult(consent_url=consent_url)

    async def handle_callback(
        self,
        user_id: str,
        code: Optional[str] = None,
        connection_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> ProviderCallbackResult:
        if not code:
            raise ValueError("Authorization code is missing")

        connection_id = str(uuid.uuid4())
        mock_access_token = f"acc-tok-{uuid.uuid4()}"
        mock_refresh_token = f"ref-tok-{uuid.uuid4()}"

        mock_transactions = [
            {
                "provider_transaction_id": "provider-txn-1",
                "date": datetime.date.today().isoformat(),
                "description": "Tesco",
                "amount": -25.50,
                "currency": "GBP",
            },
            {
                "provider_transaction_id": "provider-txn-2",
                "date": (datetime.date.today() - datetime.timedelta(days=1)).isoformat(),
                "description": "Amazon",
                "amount": -12.99,
                "currency": "GBP",
            },
        ]

        return ProviderCallbackResult(
            connection_id=connection_id,
            status="processing",
            message="Connection established. Transaction import dispatched.",
            transactions=mock_transactions,
            metadata={
                "provider_id": self.provider_id,
                "access_token": mock_access_token,
                "refresh_token": mock_refresh_token,
            },
        )
