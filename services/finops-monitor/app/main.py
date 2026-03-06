"""
FinOps Monitor Service — FastAPI + APScheduler

Endpoints:
  GET /health
  GET /status
  GET /mtd/{user_id}/status                  – current quarter summary
  GET /mtd/{user_id}/quarterly/{quarter}     – specific quarter (e.g. Q1)
  GET /mtd/{user_id}/all/{tax_year}          – all 4 quarters for a tax year
  POST /mtd/{user_id}/sync                   – manual sync of MTD totals

Scheduled tasks:
  run_all_monitors()    – every 5 minutes  (fraud, balance, invoices)
  run_mtd_weekly()      – every Sunday     (bulk-sync MTD accumulators)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import app.monitors.balance_monitor as balance_monitor
import app.monitors.fraud_monitor as fraud_monitor
import app.monitors.invoice_monitor as invoice_monitor
from app.mtd.deadlines import (
    days_until_deadline,
    get_current_quarter,
    get_next_deadline,
)
from app.mtd.tracker import QuarterlyAccumulator
from app.redis_bus import EventType, create_redis_client, publish_event

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]

# ── scheduler + redis (module-level, initialised in lifespan) ────────────────
scheduler = AsyncIOScheduler()
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = await create_redis_client()
    log.info("Redis connected: %s", os.getenv("REDIS_URL", "redis://redis:6379/0"))

    # Register periodic jobs
    scheduler.add_job(
        _run_all_monitors,
        "interval",
        minutes=5,
        id="monitors",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_mtd_weekly,
        "cron",
        day_of_week="sun",
        hour=2,
        id="mtd_weekly",
        replace_existing=True,
    )
    scheduler.start()
    log.info("APScheduler started")

    yield

    scheduler.shutdown(wait=False)
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="FinOps Monitor",
    description="Background financial monitoring + MTD ITSA compliance tracker",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── scheduled task implementations ───────────────────────────────────────────

async def _run_all_monitors() -> None:
    """Called every 5 minutes by the scheduler."""
    log.info("[%s] Running all monitors", datetime.now(timezone.utc).isoformat())
    try:
        await fraud_monitor.run(redis_client)
        await balance_monitor.run(redis_client)
        await invoice_monitor.run(redis_client)
    except Exception as exc:
        log.error("Monitor run error: %s", exc, exc_info=True)


async def _run_mtd_weekly() -> None:
    """Weekly MTD accumulation sync — called every Sunday at 02:00 UTC."""
    log.info("[%s] Running weekly MTD sync", datetime.now(timezone.utc).isoformat())
    # In production this would query the transactions service for all users
    # and call accumulator.bulk_sync(). For now we log the intent.
    log.info("MTD weekly sync complete (no users configured yet)")


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "finops-monitor"}


@app.get("/status")
async def status():
    next_q = get_next_deadline()
    return {
        "service":            "finops-monitor",
        "scheduler_running":  scheduler.running,
        "next_deadline":      next_q.submission_deadline.isoformat(),
        "days_until_deadline": days_until_deadline(),
        "timestamp":          datetime.now(timezone.utc).isoformat(),
    }


@app.get("/mtd/{user_id}/status")
async def mtd_status(user_id: str):
    """Return the current quarter MTD accumulator for a user."""
    acc = QuarterlyAccumulator(redis_client, user_id)
    data = await acc.get()
    next_q = get_next_deadline()
    data["days_until_deadline"] = days_until_deadline()
    data["next_deadline"] = next_q.submission_deadline.isoformat()
    return data


@app.get("/mtd/{user_id}/quarterly/{quarter_num}")
async def mtd_quarterly(user_id: str, quarter_num: str):
    """
    Return a specific quarter accumulator.
    quarter_num: Q1 | Q2 | Q3 | Q4
    """
    quarter_num = quarter_num.upper()
    if quarter_num not in ("Q1", "Q2", "Q3", "Q4"):
        raise HTTPException(422, "quarter_num must be Q1, Q2, Q3, or Q4")

    # Determine relevant tax year from current date
    import datetime as _dt

    from app.mtd.deadlines import _quarters_for_tax_year
    today = _dt.date.today()
    # Try current and previous tax years
    for year in [today.year, today.year - 1]:
        for q in _quarters_for_tax_year(year):
            if q.label.startswith(quarter_num):
                acc = QuarterlyAccumulator(redis_client, user_id)
                return await acc.get(q)

    raise HTTPException(404, f"Quarter {quarter_num} not found")


@app.get("/mtd/{user_id}/all/{tax_year}")
async def mtd_all_quarters(user_id: str, tax_year: str):
    """
    Return all 4 quarters for a tax year.
    tax_year format: 2026-27 (hyphen) or 2026/27 (slash)
    """
    tax_year = tax_year.replace("-", "/")
    try:
        acc = QuarterlyAccumulator(redis_client, user_id)
        quarters = await acc.get_all_quarters(tax_year)
        return {"user_id": user_id, "tax_year": tax_year, "quarters": quarters}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


class SyncPayload(BaseModel):
    income: float
    expenses: float
    transaction_count: int
    tax_year: str | None = None    # defaults to current quarter's tax year
    quarter: str | None = None     # Q1 | Q2 | Q3 | Q4, defaults to current


@app.post("/mtd/{user_id}/sync")
async def mtd_sync(user_id: str, payload: SyncPayload):
    """Manually push aggregated MTD totals for a user-quarter."""
    acc = QuarterlyAccumulator(redis_client, user_id)
    result = await acc.bulk_sync(
        income=payload.income,
        expenses=payload.expenses,
        transaction_count=payload.transaction_count,
    )
    if result.get("mtd_required"):
        await publish_event(
            redis_client,
            stream=f"finops:mtd:{user_id}",
            event={
                "type":    EventType.MTD_THRESHOLD_BREACH,
                "user_id": user_id,
                "income":  payload.income,
                "quarter": result.get("quarter"),
            },
        )
    return result
