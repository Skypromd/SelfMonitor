"""Tests for MTD deadline email reminder helpers."""

import os
import sys
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-finops")


from app.mtd.reminder_email import (  # noqa: E402
    _dedup_key,
    dispatch_daily_reminders,
)


def test_dedup_key_format():
    k = _dedup_key("user@example.com", date(2026, 8, 5), "tier-14")
    assert "user@example.com" in k
    assert "2026-08-05" in k
    assert k.endswith(":tier-14")


@pytest.mark.asyncio
async def test_dispatch_daily_reminders_no_recipients_short_circuits():
    redis = AsyncMock()
    with patch(
        "app.mtd.reminder_email.fetch_recipient_emails",
        new_callable=AsyncMock,
        return_value=[],
    ):
        out = await dispatch_daily_reminders(redis)
    assert out["recipients_checked"] == 0
