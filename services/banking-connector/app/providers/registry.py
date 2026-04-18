from typing import Dict, List
from urllib.parse import quote

from .base import BankingProvider
from .mock import MockProvider
from .saltedge import SaltedgeProvider
from .truelayer import TrueLayerProvider


def _provider_logo_url(domain: str) -> str:
    return f"https://www.google.com/s2/favicons?domain={quote(domain, safe='')}&sz=64"


_PROVIDER_DOMAINS: Dict[str, str] = {
    "mock_bank": "openbanking.org.uk",
    "saltedge": "saltedge.com",
    "truelayer": "truelayer.com",
}


PROVIDERS: Dict[str, type[BankingProvider]] = {
    "mock_bank": MockProvider,
    "saltedge": SaltedgeProvider,
    "truelayer": TrueLayerProvider,
}

# Salt Edge is the primary production connector; TrueLayer remains a dev fallback when Salt Edge keys are absent.
_PROVIDER_LIST_ORDER = ("saltedge", "truelayer", "mock_bank")


def get_provider(provider_id: str) -> BankingProvider:
    provider_class = PROVIDERS.get(provider_id)
    if not provider_class:
        raise ValueError(f"Unsupported provider '{provider_id}'.")
    return provider_class()


def list_providers() -> List[Dict[str, str]]:
    providers: List[Dict[str, str]] = []
    for provider_id in _PROVIDER_LIST_ORDER:
        provider_class = PROVIDERS.get(provider_id)
        if not provider_class:
            continue
        provider = provider_class()
        domain = _PROVIDER_DOMAINS.get(provider_id, "openbanking.org.uk")
        providers.append(
            {
                "id": provider_id,
                "display_name": provider.display_name,
                "configured": "true" if provider.is_configured() else "false",
                "logo_url": _provider_logo_url(domain),
            }
        )
    return providers
