import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-finops")
os.environ.setdefault("INTERNAL_SERVICE_SECRET", "finops-internal-test-secret")

_SMTP_PATCH = dict(SMTP_HOST="smtp.test", SMTP_USER="u", SMTP_PASSWORD="p")


def test_baseline_stores_step_without_notify():
    from app.marketing import mortgage_milestone_notify

    async def _run():
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)

        with patch.multiple(mortgage_milestone_notify, **_SMTP_PATCH):
            with patch.object(
                mortgage_milestone_notify,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_milestone_notify,
                    "_fetch_current_mortgage_step",
                    new_callable=AsyncMock,
                    return_value=("deposit", "Save your deposit"),
                ):
                    with patch.object(mortgage_milestone_notify, "_send_smtp") as smtp:
                        r = await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
                            redis
                        )
        assert r["skipped_baseline"] == 1
        assert r["notifications_sent"] == 0
        assert r.get("advance_no_channel", 0) == 0
        smtp.assert_not_called()
        redis.set.assert_called()

    asyncio.run(_run())


def test_step_change_sends_and_updates_redis():
    from app.marketing import mortgage_milestone_notify

    async def _run():
        redis = AsyncMock()

        async def _get(k: bytes | str):
            ks = k.decode("utf-8") if isinstance(k, bytes) else k
            if "mortgage:last_step:" in ks:
                return b"credit"
            return None

        redis.get = AsyncMock(side_effect=_get)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)

        with patch.multiple(mortgage_milestone_notify, **_SMTP_PATCH):
            with patch.object(
                mortgage_milestone_notify,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_milestone_notify,
                    "_fetch_current_mortgage_step",
                    new_callable=AsyncMock,
                    return_value=("deposit", "Save your deposit"),
                ):
                    with patch.object(mortgage_milestone_notify, "_send_smtp") as smtp:
                        with patch.object(
                            mortgage_milestone_notify,
                            "_registered_expo_token",
                            new_callable=AsyncMock,
                            return_value=None,
                        ):
                            r = await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
                                redis
                            )
        assert r["notifications_sent"] == 1
        smtp.assert_called_once()
        redis.delete.assert_not_called()

    asyncio.run(_run())


def test_smtp_failure_deletes_dedup_and_keeps_last_step():
    from app.marketing import mortgage_milestone_notify

    async def _run():
        redis = AsyncMock()

        async def _get(k: bytes | str):
            ks = k.decode("utf-8") if isinstance(k, bytes) else k
            if "mortgage:last_step:" in ks:
                return b"credit"
            return None

        redis.get = AsyncMock(side_effect=_get)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)

        with patch.multiple(mortgage_milestone_notify, **_SMTP_PATCH):
            with patch.object(
                mortgage_milestone_notify,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_milestone_notify,
                    "_fetch_current_mortgage_step",
                    new_callable=AsyncMock,
                    return_value=("deposit", "Save your deposit"),
                ):
                    with patch.object(
                        mortgage_milestone_notify,
                        "_send_smtp",
                        side_effect=RuntimeError("smtp down"),
                    ):
                        with patch.object(
                            mortgage_milestone_notify,
                            "_registered_expo_token",
                            new_callable=AsyncMock,
                            return_value=None,
                        ):
                            r = await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
                                redis
                            )
        assert r["notifications_sent"] == 0
        redis.delete.assert_called()

    asyncio.run(_run())


def test_no_smtp_no_push_advances_without_sent_counter():
    from app.marketing import mortgage_milestone_notify

    async def _run():
        redis = AsyncMock()

        async def _get(k: bytes | str):
            ks = k.decode("utf-8") if isinstance(k, bytes) else k
            if "mortgage:last_step:" in ks:
                return b"credit"
            return None

        redis.get = AsyncMock(side_effect=_get)
        redis.set = AsyncMock(return_value=True)

        with patch.multiple(
            mortgage_milestone_notify,
            SMTP_HOST="",
            SMTP_USER="",
            SMTP_PASSWORD="",
        ):
            with patch.object(
                mortgage_milestone_notify,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_milestone_notify,
                    "_fetch_current_mortgage_step",
                    new_callable=AsyncMock,
                    return_value=("deposit", "Save your deposit"),
                ):
                    with patch.object(mortgage_milestone_notify, "_send_smtp") as smtp:
                        with patch.object(
                            mortgage_milestone_notify,
                            "_registered_expo_token",
                            new_callable=AsyncMock,
                            return_value=None,
                        ):
                            r = await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
                                redis
                            )
        assert r["notifications_sent"] == 0
        assert r["advance_no_channel"] == 1
        smtp.assert_not_called()

    asyncio.run(_run())


def test_same_step_no_notify():
    from app.marketing import mortgage_milestone_notify

    async def _run():
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"deposit")
        redis.set = AsyncMock(return_value=True)

        with patch.multiple(mortgage_milestone_notify, **_SMTP_PATCH):
            with patch.object(
                mortgage_milestone_notify,
                "fetch_recipient_emails",
                new_callable=AsyncMock,
                return_value=["u@example.com"],
            ):
                with patch.object(
                    mortgage_milestone_notify,
                    "_fetch_current_mortgage_step",
                    new_callable=AsyncMock,
                    return_value=("deposit", "Save your deposit"),
                ):
                    with patch.object(mortgage_milestone_notify, "_send_smtp") as smtp:
                        r = await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
                            redis
                        )
        assert r["notifications_sent"] == 0
        smtp.assert_not_called()

    asyncio.run(_run())
