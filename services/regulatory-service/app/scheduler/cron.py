"""
Schedule regulatory polling (RU.15). Uses APScheduler cron — no Celery broker required.

Set REGULATORY_USE_CRON=1 for fixed times (06:00 daily, 03:00 Sunday weekly).
Default remains interval 24h for backward compatibility.
"""
from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

USE_CRON = os.environ.get("REGULATORY_USE_CRON", "").strip() in ("1", "true", "yes")


def register_regulatory_jobs(
    scheduler: AsyncIOScheduler,
    *,
    daily_job: Callable[[], Awaitable[None]],
    weekly_job: Callable[[], Awaitable[None]] | None = None,
    skip_external: bool = False,
) -> None:
    if skip_external:
        return
    if USE_CRON:
        scheduler.add_job(
            daily_job,
            CronTrigger(hour=6, minute=0),
            id="regulatory_govuk_daily",
            replace_existing=True,
        )
        if weekly_job is not None:
            scheduler.add_job(
                weekly_job,
                CronTrigger(day_of_week="sun", hour=3, minute=0),
                id="regulatory_govuk_weekly_parse",
                replace_existing=True,
            )
    else:
        scheduler.add_job(
            daily_job,
            IntervalTrigger(hours=24),
            id="hmrc_monitor",
            replace_existing=True,
        )
        if weekly_job is not None:
            scheduler.add_job(
                weekly_job,
                IntervalTrigger(weeks=1),
                id="regulatory_govuk_weekly_parse",
                replace_existing=True,
            )
