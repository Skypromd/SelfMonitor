"""Owner / user notification hooks (RU.14–18 — audit log until SMTP exists)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_owner_alert(message: str, extra: dict[str, Any] | None = None) -> None:
    logger.warning("REGULATORY_ALERT: %s %s", message, extra or {})
