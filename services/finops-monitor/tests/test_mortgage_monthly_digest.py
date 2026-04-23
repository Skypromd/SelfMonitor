import asyncio
import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-finops")
os.environ.setdefault("INTERNAL_SERVICE_SECRET", "finops-internal-test-secret")

_SMTP_PATCH = dict(SMTP_HOST="smtp.test", SMTP_USER="u", SMTP_PASSWORD="p")


def test_monthly_digest_sends_email_when_smtp_configured():
    from app.marketing import mortgage_monthly_digest

    sample = {
        "current_step_id": "deposit",
        "steps": [
            {"id": "deposit", "title": "Save deposit", "status": "current"},
        ],
        "estimated_months_to_deposit_goal": 12,
    }

    async def _run():
        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)

        with patch.multiple(mortgage_monthly_digest, **_SMTP_PATCH):
            with patch.object(
                mortgage_monthly_digest,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_monthly_digest,
                    "fetch_mortgage_progress_payload",
                    new_callable=AsyncMock,
                    return_value=sample,
                ):
                    with patch.object(mortgage_monthly_digest, "_send_smtp") as smtp:
                        with patch.object(
                            mortgage_monthly_digest,
                            "_registered_expo_token",
                            new_callable=AsyncMock,
                            return_value=None,
                        ):
                            with patch("app.marketing.mortgage_monthly_digest.date") as dmock:
                                dmock.today = lambda: date(2026, 3, 10)
                                r = await mortgage_monthly_digest.dispatch_mortgage_monthly_digest(
                                    redis
                                )
        assert r["emails_sent"] == 1
        assert r["pushes_sent"] == 0
        smtp.assert_called_once()

    asyncio.run(_run())


def test_monthly_digest_skips_when_payload_empty():
    from app.marketing import mortgage_monthly_digest

    async def _run():
        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)

        with patch.multiple(mortgage_monthly_digest, **_SMTP_PATCH):
            with patch.object(
                mortgage_monthly_digest,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_monthly_digest,
                    "fetch_mortgage_progress_payload",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    with patch.object(mortgage_monthly_digest, "_send_smtp") as smtp:
                        with patch("app.marketing.mortgage_monthly_digest.date") as dmock:
                            dmock.today = lambda: date(2026, 3, 10)
                            r = await mortgage_monthly_digest.dispatch_mortgage_monthly_digest(
                                redis
                            )
        assert r["emails_sent"] == 0
        smtp.assert_not_called()
        redis.delete.assert_called()

    asyncio.run(_run())
