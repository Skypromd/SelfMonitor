from typing import Dict, List

from .base import BankingProvider
from .mock import MockProvider
from .saltedge import SaltedgeProvider


PROVIDERS: Dict[str, type[BankingProvider]] = {
    "mock_bank": MockProvider,
    "saltedge": SaltedgeProvider,
}


def get_provider(provider_id: str) -> BankingProvider:
    provider_class = PROVIDERS.get(provider_id)
    if not provider_class:
        raise ValueError(f"Unsupported provider '{provider_id}'.")
    return provider_class()


def list_providers() -> List[Dict[str, str]]:
    providers = []
    for provider_id, provider_class in PROVIDERS.items():
        provider = provider_class()
        providers.append(
            {
                "id": provider_id,
                "display_name": provider.display_name,
                "configured": "true" if provider.is_configured() else "false",
            }
        )
    return providers
