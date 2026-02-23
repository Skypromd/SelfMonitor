from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class ProviderInitResult:
    consent_url: str
    state: Optional[str] = None


@dataclass
class ProviderCallbackResult:
    connection_id: str
    status: str
    message: str
    transactions: List[Dict]
    metadata: Dict


class BankingProvider:
    provider_id: str = "base"
    display_name: str = "Base Provider"

    def is_configured(self) -> bool:
        return True

    async def initiate(self, user_id: str, redirect_uri: str) -> ProviderInitResult:
        raise NotImplementedError

    async def handle_callback(
        self,
        user_id: str,
        code: Optional[str] = None,
        connection_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> ProviderCallbackResult:
        raise NotImplementedError
