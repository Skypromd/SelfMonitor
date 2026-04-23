"""
FinOps Monitor Service — FastAPI + APScheduler

Endpoints:
  GET /health
  GET /status
  GET /mtd/{user_id}/status                  – current quarter summary
  GET /mtd/{user_id}/quarterly/{quarter}     – specific quarter (e.g. Q1)
  GET /mtd/{user_id}/all/{tax_year}          – all 4 quarters for a tax year
  POST /mtd/{user_id}/sync                   – manual sync of MTD totals
  POST /mtd/me/expo-push-token               – register Expo push token (JWT)
  DELETE /mtd/me/expo-push-token             – remove Expo push token (JWT)

Scheduled tasks:
  run_all_monitors()    – every 5 minutes  (fraud, balance, invoices)
  run_mtd_weekly()      – every Sunday     (bulk-sync MTD accumulators)
  run_mtd_reminders     – daily 08:05 UTC (MTD deadline email + Expo push)
  run_mortgage_milestones – weekly Thu 09:25 UTC (Road to mortgage step change email + push)
  run_mortgage_monthly_digest – monthly 10th 09:35 UTC (Road to mortgage summary email + push)
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

for _parent in Path(__file__).resolve().parents:
    if (_parent / "libs").exists():
        _root = str(_parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

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
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()

_get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()
_EXPO_PUSH_TOKEN_TTL = int(os.getenv("FINOPS_EXPO_PUSH_TTL_SECONDS", str(120 * 86400)))

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
    scheduler.add_job(
        _run_mtd_email_reminders,
        "cron",
        hour=8,
        minute=5,
        id="mtd_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_tax_savings_monthly_push,
        "cron",
        day=15,
        hour=9,
        minute=10,
        id="tax_tips_monthly_push",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_referral_invite_emails,
        "cron",
        day=5,
        hour=10,
        minute=15,
        id="referral_invite_email",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_mortgage_milestone_notifications,
        "cron",
        day_of_week="thu",
        hour=9,
        minute=25,
        id="mortgage_milestones_weekly",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_mortgage_monthly_digest,
        "cron",
        day=10,
        hour=9,
        minute=35,
        id="mortgage_monthly_digest",
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

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
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


async def _run_mtd_email_reminders() -> None:
    if redis_client is None:
        return
    log.info("[%s] MTD email reminders", datetime.now(timezone.utc).isoformat())
    try:
        from app.mtd import reminder_email

        await reminder_email.dispatch_daily_reminders(redis_client)
    except Exception as exc:
        log.error("MTD email reminders error: %s", exc, exc_info=True)


async def _run_tax_savings_monthly_push() -> None:
    if redis_client is None:
        return
    try:
        from app.marketing import tax_savings_monthly_push

        await tax_savings_monthly_push.dispatch_tax_savings_monthly_push(redis_client)
    except Exception as exc:
        log.error("Tax savings monthly push error: %s", exc, exc_info=True)


async def _run_referral_invite_emails() -> None:
    if redis_client is None:
        return
    try:
        from app.marketing import referral_invite_email

        await referral_invite_email.dispatch_referral_invite_emails(redis_client)
    except Exception as exc:
        log.error("Referral invite email campaign error: %s", exc, exc_info=True)


async def _run_mortgage_milestone_notifications() -> None:
    if redis_client is None:
        return
    try:
        from app.marketing import mortgage_milestone_notify

        await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
            redis_client
        )
    except Exception as exc:
        log.error("Mortgage milestone notifications error: %s", exc, exc_info=True)


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


class ExpoPushTokenPayload(BaseModel):
    expo_push_token: str = Field(..., min_length=24, max_length=512)


class InvoicePaidNotifyPayload(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=512)
    invoice_id: str = Field(..., min_length=1, max_length=64)
    invoice_number: str = Field(..., min_length=1, max_length=64)
    amount_gbp: str = Field(..., min_length=1, max_length=32)
    checkout_session_id: str = Field(default="", max_length=128)


class DashboardTransactionEventPayload(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=512)


def _expo_push_redis_key(user_id: str) -> str:
    return f"mtd:expo_push:{user_id.strip().lower()}"


@app.post("/mtd/me/expo-push-token")
async def register_expo_push_token(
    payload: ExpoPushTokenPayload,
    user_id: str = Depends(get_current_user_id),
):
    from app.mtd.expo_push import validate_expo_push_token_format

    if not validate_expo_push_token_format(payload.expo_push_token):
        raise HTTPException(status_code=422, detail="invalid_expo_push_token")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    await redis_client.set(
        _expo_push_redis_key(user_id),
        payload.expo_push_token.strip(),
        ex=_EXPO_PUSH_TOKEN_TTL,
    )
    return {"ok": True}


@app.delete("/mtd/me/expo-push-token")
async def delete_expo_push_token(user_id: str = Depends(get_current_user_id)):
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    await redis_client.delete(_expo_push_redis_key(user_id))
    return {"ok": True}


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


@app.post("/internal/mtd-reminders/run")
async def internal_run_mtd_reminders(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
):
    if not INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=503, detail="internal_calls_not_configured")
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    from app.mtd import reminder_email

    return await reminder_email.dispatch_daily_reminders(redis_client)


@app.post("/internal/mortgage-milestones/run")
async def internal_run_mortgage_milestones(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
):
    if not INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=503, detail="internal_calls_not_configured")
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    from app.marketing import mortgage_milestone_notify

    return await mortgage_milestone_notify.dispatch_mortgage_milestone_notifications(
        redis_client
    )


@app.post("/internal/mortgage-monthly-digest/run")
async def internal_run_mortgage_monthly_digest(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
):
    if not INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=503, detail="internal_calls_not_configured")
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    from app.marketing import mortgage_monthly_digest

    return await mortgage_monthly_digest.dispatch_mortgage_monthly_digest(redis_client)


@app.post("/internal/notify-invoice-paid")
async def internal_notify_invoice_paid(
    body: InvoicePaidNotifyPayload,
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
):
    if not INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=503, detail="internal_calls_not_configured")
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    from app.notifications import invoice_paid_notify

    return await invoice_paid_notify.handle_invoice_paid_notify(
        redis_client,
        user_id=body.user_id,
        invoice_id=body.invoice_id,
        invoice_number=body.invoice_number,
        amount_gbp=body.amount_gbp,
        checkout_session_id=body.checkout_session_id,
    )


@app.websocket("/ws/dashboard/live")
async def ws_dashboard_live(websocket: WebSocket):
    if redis_client is None:
        await websocket.close(code=1011, reason="redis_unavailable")
        return
    from app.dashboard_live import websocket_dashboard_live as run_dashboard_ws

    await run_dashboard_ws(
        websocket=websocket,
        redis_client=redis_client,
        auth_secret_key=AUTH_SECRET_KEY,
        auth_algorithm=AUTH_ALGORITHM,
    )


@app.post("/internal/dashboard-transaction-event")
async def internal_dashboard_transaction_event(
    body: DashboardTransactionEventPayload,
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
):
    if not INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=503, detail="internal_calls_not_configured")
    if not x_internal_token or x_internal_token != INTERNAL_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    if redis_client is None:
        raise HTTPException(status_code=503, detail="redis_unavailable")
    from app.dashboard_live import publish_dashboard_refresh

    n = await publish_dashboard_refresh(redis_client, user_id=body.user_id)
    return {"subscribers": n}
