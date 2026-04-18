"""Tests for MTD deadline email reminder helpers."""

import asyncio
import os
import sys
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-finops")


from app.mtd.reminder_email import (  # noqa: E402
    _dedup_key,
    dispatch_daily_reminders,
    process_user_day,
)


def test_dedup_key_format():
    k = _dedup_key("user@example.com", date(2026, 8, 5), "tier-14")
    assert "user@example.com" in k
    assert "2026-08-05" in k
    assert k.endswith(":tier-14")


def test_process_user_day_tier_three_includes_draft_prep_hint():
    async def _run() -> None:
        redis = AsyncMock()
        next_q = SimpleNamespace(label="Q1 2026/27", submission_deadline=date(2026, 8, 5))
        with patch("app.mtd.reminder_email._send_reminder_channels", new_callable=AsyncMock) as send:
            with patch("app.mtd.reminder_email.get_next_deadline", return_value=next_q):
                with patch("app.mtd.reminder_email.QuarterlyAccumulator") as acc_cls:
                    acc_inst = acc_cls.return_value
                    acc_inst.get = AsyncMock(return_value={"status": ""})
                    await process_user_day(
                        redis,
                        user_id="user@example.com",
                        to_email="user@example.com",
                        today=date(2026, 8, 2),
                    )
        tier3 = [c for c in send.call_args_list if c.kwargs.get("kind") == "tier-3"]
        assert len(tier3) == 1
        assert "draft" in tier3[0].kwargs["body"].lower()
        assert tier3[0].kwargs["extra_event"].get("mtd_draft_prep_hint") is True

    asyncio.run(_run())


def test_dispatch_daily_reminders_no_recipients_short_circuits():
    async def _run() -> dict:
        redis = AsyncMock()
        with patch(
            "app.mtd.reminder_email.fetch_recipient_emails",
            new_callable=AsyncMock,
            return_value=[],
        ):
            return await dispatch_daily_reminders(redis)

    assert asyncio.run(_run())["recipients_checked"] == 0
