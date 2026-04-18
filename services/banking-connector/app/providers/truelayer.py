import os

from .base import BankingProvider


class TrueLayerProvider(BankingProvider):
    """UK Open Banking via TrueLayer — consent + token exchange live in app.main."""

    provider_id = "truelayer"
    display_name = "TrueLayer (UK Open Banking)"

    def is_configured(self) -> bool:
        return bool(os.getenv("TRUELAYER_CLIENT_ID", "").strip())
