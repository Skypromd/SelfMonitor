"""
Billing Service — Internal accounting + Stripe integration for SelfMonitor
Handles checkout sessions, webhooks, subscription management, invoice generation,
automatic invoice dispatch (SMTP), payment tracking, and revenue analytics.

Dev mode: if STRIPE_SECRET_KEY is not set, returns a mock checkout URL pointing
directly to the registration page (no actual payment is taken).
"""
import datetime
import email.mime.multipart
import email.mime.text
import json
import logging
import os
import smtplib
import sqlite3
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional

import httpx
import stripe
from apscheduler.schedulers.background import (
    BackgroundScheduler,  # type: ignore[import-untyped]
)
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:80")
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "")
DEV_MODE = not bool(STRIPE_SECRET_KEY)

# ── SMTP ───────────────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

if not DEV_MODE:
    stripe.api_key = STRIPE_SECRET_KEY

DB_PATH = os.getenv(
    "BILLING_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "billing.db"),
)

# ── Plan definitions ──────────────────────────────────────────────────────────
PLANS: dict[str, dict] = {
    "free":         {"name": "Free",         "amount": 0,    "currency": "gbp", "interval": None,    "price_id": os.getenv("STRIPE_PRICE_FREE", "")},
    "starter":      {"name": "Starter",      "amount": 1500, "currency": "gbp", "interval": "month", "price_id": os.getenv("STRIPE_PRICE_STARTER", "")},
    "growth":       {"name": "Growth",       "amount": 1800, "currency": "gbp", "interval": "month", "price_id": os.getenv("STRIPE_PRICE_GROWTH", "")},
    "pro":          {"name": "Pro",          "amount": 2100, "currency": "gbp", "interval": "month", "price_id": os.getenv("STRIPE_PRICE_PRO", "")},
    "business":     {"name": "Business",     "amount": 3000, "currency": "gbp", "interval": "month", "price_id": os.getenv("STRIPE_PRICE_BUSINESS", "")},
}
PLAN_AMOUNT_GBP = {k: v["amount"] / 100 for k, v in PLANS.items()}

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Billing Service",
    description="Internal accounting, Stripe payments, invoice auto-dispatch, revenue analytics.",
    version="2.0.0",
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


def _claim_stripe_webhook_event(event_id: str) -> bool:
    """Return True if this is the first time we see event_id (should process)."""
    if not event_id:
        return True
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO stripe_webhook_events (event_id, received_at) VALUES (?, ?)",
                (event_id, int(time.time())),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# ── Database ───────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        # --- Subscriptions ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                status TEXT NOT NULL DEFAULT 'inactive',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                stripe_session_id TEXT,
                current_period_end INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sub_email ON subscriptions(email)")

        # --- Invoices ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                invoice_number TEXT NOT NULL,
                subscription_id INTEGER,
                user_email TEXT NOT NULL,
                plan TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'GBP',
                status TEXT NOT NULL DEFAULT 'pending',
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                due_date TEXT NOT NULL,
                paid_at TEXT,
                sent_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_email    ON invoices(user_email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_status   ON invoices(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_due      ON invoices(due_date)")

        # --- Payments ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                user_email TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'GBP',
                method TEXT NOT NULL DEFAULT 'stripe',
                status TEXT NOT NULL DEFAULT 'success',
                transaction_ref TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pay_invoice ON payments(invoice_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pay_email   ON payments(user_email)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                event_id TEXT PRIMARY KEY,
                received_at INTEGER NOT NULL
            )
        """)

        conn.commit()

    # Seed demo data when DB is empty (dev / fresh install)
    _seed_demo_data()


# ── Demo seed ──────────────────────────────────────────────────────────────────
def _seed_demo_data() -> None:
    """Populate with realistic demo subscriptions + invoices if tables are empty."""
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0] > 0:
            return   # already seeded

        now = int(time.time())
        demo_subs = [
            ("alice@example.com",   "business",  "active",    now - 200*86400),
            ("bob@example.com",     "pro",        "active",    now - 150*86400),
            ("carol@example.com",   "growth",     "active",    now - 120*86400),
            ("dan@example.com",     "starter",    "active",    now - 90*86400),
            ("eve@example.com",     "business",  "trialing",  now - 20*86400),
            ("frank@example.com",   "pro",        "active",    now - 180*86400),
            ("grace@example.com",   "growth",     "cancelled", now - 60*86400),
            ("harry@example.com",   "starter",    "active",    now - 45*86400),
            ("ivan@example.com",    "business",  "active",    now - 300*86400),
            ("julia@example.com",   "pro",        "active",    now - 230*86400),
            ("kyle@example.com",    "starter",    "inactive",  now - 400*86400),
            ("lena@example.com",    "growth",     "active",    now - 75*86400),
        ]

        sub_ids = {}
        for email, plan, status, created in demo_subs:
            cur = conn.execute(
                "INSERT INTO subscriptions (email,plan,status,created_at,updated_at) VALUES (?,?,?,?,?)",
                (email, plan, status, created, now)
            )
            sub_ids[email] = cur.lastrowid

        # Generate retroactive monthly invoices for each active/past sub
        inv_rows = []
        pay_rows = []
        today = datetime.date.today()
        inv_counter = 1

        for email, plan, status, created in demo_subs:
            amount = PLAN_AMOUNT_GBP.get(plan, 0)
            if amount == 0:
                continue
            start_date = datetime.date.fromtimestamp(created)
            cur_date = start_date.replace(day=1)
            while cur_date <= today:
                inv_id = str(uuid.uuid4())
                inv_num = f"INV-{inv_counter:05d}"
                inv_counter += 1
                period_end = (cur_date.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
                due = period_end + datetime.timedelta(days=7)
                # Determine status
                if due < today - datetime.timedelta(days=14):
                    inv_status = "paid"
                    paid_at = str(due + datetime.timedelta(days=3))
                    sent_at = str(cur_date)
                elif due < today:
                    inv_status = "overdue" if status != "active" else "paid"
                    paid_at = str(due) if inv_status == "paid" else None
                    sent_at = str(cur_date)
                else:
                    inv_status = "sent" if status == "active" else "pending"
                    paid_at = None
                    sent_at = str(cur_date) if inv_status == "sent" else None

                inv_rows.append((
                    inv_id, inv_num, sub_ids[email], email, plan, amount, "GBP",
                    inv_status, str(cur_date), str(period_end), str(due),
                    paid_at, sent_at, None, str(cur_date)
                ))

                if inv_status == "paid":
                    pay_rows.append((
                        str(uuid.uuid4()), inv_id, email, amount, "GBP", "stripe", "success",
                        f"ch_{uuid.uuid4().hex[:16]}", str(paid_at)
                    ))

                # Next month
                next_month = cur_date.month % 12 + 1
                next_year = cur_date.year + (1 if cur_date.month == 12 else 0)
                cur_date = cur_date.replace(year=next_year, month=next_month, day=1)

        conn.executemany(
            "INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", inv_rows
        )
        conn.executemany(
            "INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?)", pay_rows
        )
        conn.commit()


# ── Scheduler — auto-generate monthly invoices ────────────────────────────────
def _auto_generate_invoices() -> None:
    """
    Runs daily. For every active subscription whose next billing date has passed
    and no invoice exists for the current period, generates a new invoice and
    emails it to the customer.
    """
    today = datetime.date.today()
    today_str = str(today)

    with get_db() as conn:
        active_subs = conn.execute(
            "SELECT * FROM subscriptions WHERE status IN ('active','trialing')"
        ).fetchall()

        for sub in active_subs:
            email_addr = sub["email"]
            plan = sub["plan"]
            amount = PLAN_AMOUNT_GBP.get(plan, 0)
            if amount == 0:
                continue

            # Check if invoice for this period already exists
            period_start = today.replace(day=1)
            existing = conn.execute(
                "SELECT id FROM invoices WHERE subscription_id=? AND period_start=?",
                (sub["id"], str(period_start))
            ).fetchone()
            if existing:
                continue

            # Generate invoice
            inv_id = str(uuid.uuid4())
            inv_num = _next_invoice_number(conn)
            period_end_raw = (period_start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
            due_date = period_end_raw + datetime.timedelta(days=7)

            conn.execute(
                "INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (inv_id, inv_num, sub["id"], email_addr, plan, amount, "GBP",
                 "sent", str(period_start), str(period_end_raw), str(due_date),
                 None, today_str, None, today_str)
            )
            conn.commit()

            # Send email
            try:
                _send_invoice_email(email_addr, inv_num, plan, amount, str(period_start), str(due_date))
            except Exception as exc:
                logger.warning("Invoice email failed for %s: %s", email_addr, exc)

    logger.info("Auto-invoice job complete (%s)", today_str)


def _next_invoice_number(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()
    n = (row[0] or 0) + 1
    return f"INV-{n:05d}"


def _send_invoice_email(to_email: str, inv_num: str, plan: str, amount: float, period: str, due: str) -> None:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        logger.info("SMTP not configured — invoice %s not emailed to %s", inv_num, to_email)
        return

    amount_str = f"£{amount:.2f}"
    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["Subject"] = f"SelfMonitor Invoice {inv_num} — {amount_str}"
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:32px">
    <div style="max-width:520px;margin:0 auto;background:#1e293b;border-radius:12px;padding:32px">
      <h1 style="color:#14b8a6;margin:0 0 4px">SelfMonitor</h1>
      <p style="color:#64748b;margin:0 0 24px;font-size:14px">Monthly Invoice</p>
      <hr style="border:none;border-top:1px solid #334155;margin-bottom:24px">
      <table style="width:100%;font-size:15px">
        <tr><td style="color:#94a3b8">Invoice</td><td style="text-align:right;font-weight:700">{inv_num}</td></tr>
        <tr><td style="color:#94a3b8">Plan</td><td style="text-align:right">{plan.title()}</td></tr>
        <tr><td style="color:#94a3b8">Period</td><td style="text-align:right">{period}</td></tr>
        <tr><td style="color:#94a3b8">Due date</td><td style="text-align:right">{due}</td></tr>
        <tr><td colspan="2"><hr style="border:none;border-top:1px solid #334155;margin:16px 0"></td></tr>
        <tr><td style="font-size:18px;font-weight:700">Total</td>
            <td style="text-align:right;font-size:22px;font-weight:700;color:#14b8a6">{amount_str}</td></tr>
      </table>
      <p style="margin-top:28px;font-size:13px;color:#64748b">
        Thank you for using SelfMonitor. Log in at
        <a href="http://localhost:3000" style="color:#14b8a6">localhost:3000</a>
        to view your billing history.
      </p>
    </div></body></html>
    """
    msg.attach(email.mime.text.MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_USER, to_email, msg.as_string())


# ── Startup / Shutdown ─────────────────────────────────────────────────────────
_scheduler: Optional[BackgroundScheduler] = None


@app.on_event("startup")
def startup() -> None:
    global _scheduler
    init_db()
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_auto_generate_invoices, "cron", hour=6, minute=0)
    _scheduler.start()
    if DEV_MODE:
        logger.warning("Billing service in DEV MODE — no live Stripe payments.")


@app.on_event("shutdown")
def shutdown() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)


# ══════════════════════════════════════════════════════════════════════════════
# ── Schemas ────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
class CheckoutRequest(BaseModel):
    plan: str
    email: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    dev_mode: bool


class SubscriptionInfo(BaseModel):
    email: str
    plan: str
    status: str
    current_period_end: Optional[int] = None


class InvoiceCreate(BaseModel):
    user_email: str
    plan: str
    amount: Optional[float] = None
    period_start: Optional[str] = None    # yyyy-mm-dd
    period_end: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None


class InvoicePatch(BaseModel):
    status: Optional[str] = None
    paid_at: Optional[str] = None
    notes: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# ── Core endpoints ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dev_mode": DEV_MODE}


@app.get("/plans")
def list_plans() -> dict:
    return {
        key: {"name": val["name"], "amount": val["amount"],
              "currency": val["currency"], "interval": val["interval"]}
        for key, val in PLANS.items()
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── Stripe checkout ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/checkout/session", response_model=CheckoutResponse)
async def create_checkout_session(body: CheckoutRequest) -> CheckoutResponse:
    plan_key = body.plan.lower()
    plan = PLANS.get(plan_key)
    if plan is None:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    if plan["amount"] == 0:
        return CheckoutResponse(checkout_url=f"{FRONTEND_URL}/register?plan={plan_key}", session_id="free", dev_mode=DEV_MODE)

    success_url = f"{FRONTEND_URL}/checkout-success?plan={plan_key}&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url  = f"{FRONTEND_URL}/checkout-cancel?plan={plan_key}"

    if DEV_MODE:
        mock_id = f"dev_session_{plan_key}_{int(time.time())}"
        return CheckoutResponse(checkout_url=f"{FRONTEND_URL}/checkout-success?plan={plan_key}&session_id={mock_id}&dev=1", session_id=mock_id, dev_mode=True)

    try:
        params: dict = {
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"plan": plan_key},
            "subscription_data": {"trial_period_days": 14, "metadata": {"plan": plan_key}},
        }
        if plan.get("price_id"):
            params["line_items"] = [{"price": plan["price_id"], "quantity": 1}]
        else:
            params["line_items"] = [{"price_data": {"currency": plan["currency"], "unit_amount": plan["amount"], "recurring": {"interval": plan["interval"]}, "product_data": {"name": f"SelfMonitor {plan['name']}"}}, "quantity": 1}]
        if body.email:
            params["customer_email"] = body.email
        session = stripe.checkout.Session.create(**params)
        return CheckoutResponse(checkout_url=session.url, session_id=session.id, dev_mode=False)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(exc)}") from exc


@app.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
) -> dict:
    payload = await request.body()

    if not DEV_MODE:
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=503,
                detail="STRIPE_WEBHOOK_SECRET must be set when STRIPE_SECRET_KEY is configured.",
            )
        if not stripe_signature:
            raise HTTPException(
                status_code=400,
                detail="Missing Stripe-Signature header",
            )
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError as exc:
            raise HTTPException(status_code=400, detail="Invalid signature") from exc
        event_id = str(getattr(event, "id", "") or "")
        event_type = str(event.type)
        so = event.data.object
    elif STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError as exc:
            raise HTTPException(status_code=400, detail="Invalid signature") from exc
        event_id = str(getattr(event, "id", "") or "")
        event_type = str(event.type)
        so = event.data.object
    else:
        try:
            event_dict = json.loads(payload)
        except Exception:
            return {"status": "ignored"}
        event_id = str(event_dict.get("id") or "")
        event_type = str(event_dict.get("type") or "")
        so = (event_dict.get("data") or {}).get("object") or {}

    if event_id and not _claim_stripe_webhook_event(event_id):
        logger.info("stripe webhook duplicate event_id=%s", event_id)
        return {"status": "ok", "duplicate": True}

    if event_type == "checkout.session.completed":
        customer_email = so.get("customer_email") or so.get("customer_details", {}).get(
            "email", ""
        )
        plan = so.get("metadata", {}).get("plan", "starter")
        if customer_email:
            _upsert_subscription(
                email=customer_email,
                plan=plan,
                status="trialing" if so.get("subscription") else "active",
                stripe_customer_id=so.get("customer", ""),
                stripe_subscription_id=so.get("subscription", ""),
                stripe_session_id=so.get("id", ""),
            )

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        with get_db() as conn:
            conn.execute(
                "UPDATE subscriptions SET status=?,current_period_end=?,updated_at=? WHERE stripe_subscription_id=?",
                (
                    so.get("status", "inactive"),
                    so.get("current_period_end"),
                    int(time.time()),
                    so.get("id", ""),
                ),
            )
            conn.commit()

    return {"status": "ok"}


@app.get("/subscription/{email}", response_model=SubscriptionInfo)
def get_subscription(email: str) -> SubscriptionInfo:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM subscriptions WHERE email=? ORDER BY updated_at DESC LIMIT 1", (email,)).fetchone()
    if not row:
        return SubscriptionInfo(email=email, plan="free", status="none")
    return SubscriptionInfo(email=email, plan=row["plan"], status=row["status"], current_period_end=row["current_period_end"])


# ══════════════════════════════════════════════════════════════════════════════
# ── Subscriptions list (admin) ─────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    status: Optional[str] = None,
    plan: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    q = "SELECT * FROM subscriptions WHERE 1=1"
    params: list = []
    if status:
        q += " AND status=?"; params.append(status)
    if plan:
        q += " AND plan=?"; params.append(plan)
    q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    with get_db() as conn:
        rows = conn.execute(q, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM subscriptions" + (" WHERE status=?" if status else ""), ([status] if status else [])).fetchone()[0]

    return {
        "total": total,
        "items": [dict(r) for r in rows],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── Invoices ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/invoices")
async def list_invoices(
    user_email: Optional[str] = None,
    status: Optional[str] = None,
    plan: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    q = "SELECT * FROM invoices WHERE 1=1"
    params: list = []
    if user_email:
        q += " AND user_email=?"; params.append(user_email)
    if status:
        q += " AND status=?"; params.append(status)
    if plan:
        q += " AND plan=?"; params.append(plan)
    q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    with get_db() as conn:
        rows = conn.execute(q, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]

    return {"total": total, "items": [dict(r) for r in rows]}


@app.post("/invoices")
async def create_invoice(body: InvoiceCreate) -> dict:
    today = datetime.date.today()
    amount = body.amount if body.amount is not None else PLAN_AMOUNT_GBP.get(body.plan, 0)
    period_start = body.period_start or str(today.replace(day=1))
    if body.period_end:
        period_end = body.period_end
    else:
        ps = datetime.date.fromisoformat(period_start)
        period_end = str((ps.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1))
    due_date = body.due_date or str(datetime.date.fromisoformat(period_end) + datetime.timedelta(days=7))

    inv_id = str(uuid.uuid4())
    sub_id: Optional[int] = None
    with get_db() as conn:
        sub = conn.execute("SELECT id FROM subscriptions WHERE email=? ORDER BY created_at DESC LIMIT 1", (body.user_email,)).fetchone()
        if sub:
            sub_id = sub["id"]
        inv_num = _next_invoice_number(conn)
        now_str = str(today)
        conn.execute(
            "INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (inv_id, inv_num, sub_id, body.user_email, body.plan, amount, "GBP", "pending", period_start, period_end, due_date, None, None, body.notes, now_str)
        )
        conn.commit()
    return {"id": inv_id, "invoice_number": inv_num, "status": "pending"}


@app.patch("/invoices/{invoice_id}")
async def update_invoice(invoice_id: str, body: InvoicePatch) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        updates = {}
        if body.status:
            updates["status"] = body.status
        if body.paid_at:
            updates["paid_at"] = body.paid_at
        if body.notes is not None:
            updates["notes"] = body.notes
        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE invoices SET {set_clause} WHERE id=?", list(updates.values()) + [invoice_id])
            conn.commit()
    return {"id": invoice_id, **updates}


@app.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        row = dict(row)

    try:
        _send_invoice_email(
            to_email=row["user_email"],
            inv_num=row["invoice_number"],
            plan=row["plan"],
            amount=row["amount"],
            period=row["period_start"],
            due=row["due_date"],
        )
        email_sent = True
    except Exception as exc:
        logger.warning("Email send failed: %s", exc)
        email_sent = False

    with get_db() as conn:
        conn.execute(
            "UPDATE invoices SET status='sent', sent_at=? WHERE id=?",
            (str(datetime.date.today()), invoice_id)
        )
        conn.commit()

    return {"id": invoice_id, "status": "sent", "email_sent": email_sent}


@app.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(invoice_id: str) -> dict:
    today_str = str(datetime.date.today())
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        row = dict(row)
        conn.execute("UPDATE invoices SET status='paid', paid_at=? WHERE id=?", (today_str, invoice_id))
        pay_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?)",
            (pay_id, invoice_id, row["user_email"], row["amount"], row["currency"], "manual", "success", f"manual_{pay_id[:8]}", today_str)
        )
        conn.commit()
    return {"id": invoice_id, "status": "paid", "payment_id": pay_id}


@app.post("/invoices/generate-batch")
async def generate_batch_invoices() -> dict:
    """Manually trigger the auto-invoice generator."""
    _auto_generate_invoices()
    return {"status": "ok", "message": "Batch invoice generation complete"}


# ══════════════════════════════════════════════════════════════════════════════
# ── Payments ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/payments")
async def list_payments(
    user_email: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    q = "SELECT * FROM payments WHERE 1=1"
    params: list = []
    if user_email:
        q += " AND user_email=?"; params.append(user_email)
    q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_db() as conn:
        rows = conn.execute(q, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    return {"total": total, "items": [dict(r) for r in rows]}


# ══════════════════════════════════════════════════════════════════════════════
# ── Analytics ──────────────────────────────────────════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/analytics/overview")
async def analytics_overview() -> dict:
    """
    KPI summary: MRR, ARR, active subscriptions, total invoiced, outstanding, collected.
    """
    with get_db() as conn:
        subs = conn.execute("SELECT plan, status FROM subscriptions").fetchall()
        inv_stats = conn.execute("""
            SELECT
                COUNT(*) as total_invoices,
                SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) as revenue_collected,
                SUM(CASE WHEN status IN ('pending','sent') THEN amount ELSE 0 END) as revenue_outstanding,
                SUM(CASE WHEN status='overdue' THEN amount ELSE 0 END) as revenue_overdue,
                SUM(amount) as total_invoiced
            FROM invoices
        """).fetchone()

        # Active sub counts
        plan_counts: dict[str, int] = defaultdict(int)
        for s in subs:
            if s["status"] in ("active", "trialing"):
                plan_counts[s["plan"]] += 1

        mrr = sum(PLAN_AMOUNT_GBP.get(p, 0) * n for p, n in plan_counts.items())
        active_count = sum(plan_counts.values())
        total_subs = len(subs)
        cancelled = sum(1 for s in subs if s["status"] == "cancelled")

    return {
        "mrr": round(mrr, 2),
        "arr": round(mrr * 12, 2),
        "active_subscriptions": active_count,
        "total_subscriptions": total_subs,
        "cancelled_subscriptions": cancelled,
        "churn_rate": round(cancelled / max(total_subs, 1) * 100, 1),
        "total_invoiced": round(inv_stats["total_invoiced"] or 0, 2),
        "revenue_collected": round(inv_stats["revenue_collected"] or 0, 2),
        "revenue_outstanding": round(inv_stats["revenue_outstanding"] or 0, 2),
        "revenue_overdue": round(inv_stats["revenue_overdue"] or 0, 2),
        "collection_rate": round(
            (inv_stats["revenue_collected"] or 0) / max(inv_stats["total_invoiced"] or 1, 1) * 100, 1
        ),
    }


@app.get("/analytics/revenue")
async def analytics_revenue(months: int = Query(12, ge=1, le=36)) -> dict:
    """Monthly revenue (collected + outstanding) for the last N months."""
    today = datetime.date.today()
    result = []
    for i in range(months - 1, -1, -1):
        # Work backwards month by month
        target = today.replace(day=1)
        # subtract i months
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12; y -= 1
        while m > 12:
            m -= 12; y += 1
        month_start = datetime.date(y, m, 1)
        month_end = (month_start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)

        with get_db() as conn:
            row = conn.execute("""
                SELECT
                    SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) as collected,
                    SUM(CASE WHEN status IN ('sent','pending','overdue') THEN amount ELSE 0 END) as outstanding,
                    COUNT(*) as invoices
                FROM invoices
                WHERE period_start >= ? AND period_start <= ?
            """, (str(month_start), str(month_end))).fetchone()

        result.append({
            "month": month_start.strftime("%b %Y"),
            "collected": round(row["collected"] or 0, 2),
            "outstanding": round(row["outstanding"] or 0, 2),
            "total": round((row["collected"] or 0) + (row["outstanding"] or 0), 2),
            "invoices": row["invoices"] or 0,
        })

    return {"data": result}


@app.get("/analytics/plans")
async def analytics_plans() -> dict:
    """Subscription count and MRR by plan."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT plan, status, COUNT(*) as cnt
            FROM subscriptions GROUP BY plan, status
        """).fetchall()

    plans_map: dict[str, dict] = {}
    for r in rows:
        p = r["plan"] or "free"
        if p not in plans_map:
            plans_map[p] = {"plan": p, "name": PLANS.get(p, {}).get("name", p.title()), "active": 0, "trialing": 0, "cancelled": 0, "total": 0, "mrr": 0.0}
        plans_map[p]["total"] += r["cnt"]
        st = r["status"] or "inactive"
        if st in plans_map[p]:
            plans_map[p][st] += r["cnt"]
        if st in ("active", "trialing"):
            plans_map[p]["mrr"] += PLAN_AMOUNT_GBP.get(p, 0) * r["cnt"]

    result = sorted(plans_map.values(), key=lambda x: x["mrr"], reverse=True)
    return {"data": result}


@app.get("/analytics/invoice-status")
async def analytics_invoice_status() -> dict:
    """Invoice counts by status (for donut/pie chart)."""
    with get_db() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as cnt, SUM(amount) as total FROM invoices GROUP BY status").fetchall()
    return {"data": [{"status": r["status"], "count": r["cnt"], "total": round(r["total"] or 0, 2)} for r in rows]}


@app.get("/analytics/mrr-trend")
async def analytics_mrr_trend(months: int = Query(12, ge=1, le=36)) -> dict:
    """Estimated MRR each month based on active subscriptions at billing date."""
    today = datetime.date.today()
    result = []
    with get_db() as conn:
        for i in range(months - 1, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0: m += 12; y -= 1
            month_start = datetime.date(y, m, 1)
            month_end = (month_start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)

            # Subs created before month_end and not cancelled before month_start
            rows = conn.execute("""
                SELECT plan, status FROM subscriptions
                WHERE created_at <= ? AND (status NOT IN ('cancelled','inactive') OR updated_at >= ?)
            """, (int(month_end.strftime("%s") if hasattr(month_end, "strftime") else time.mktime(month_end.timetuple())),
                  int(time.mktime(month_start.timetuple())))).fetchall()

            mrr = sum(PLAN_AMOUNT_GBP.get(r["plan"], 0) for r in rows if r["status"] in ("active", "trialing"))
            result.append({"month": month_start.strftime("%b %Y"), "mrr": round(mrr, 2), "subscribers": len(rows)})

    return {"data": result}


# ══════════════════════════════════════════════════════════════════════════════
# ── Legacy admin stats endpoint ────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/admin/stats")
async def admin_stats(request: Request) -> dict:
    with get_db() as conn:
        rows = conn.execute("SELECT plan, status, COUNT(*) as cnt FROM subscriptions GROUP BY plan, status").fetchall()
        total_row = conn.execute("SELECT COUNT(*) as cnt FROM subscriptions").fetchone()
        recent = conn.execute("SELECT email,plan,status,created_at,stripe_subscription_id FROM subscriptions ORDER BY created_at DESC LIMIT 20").fetchall()

    plan_map: dict[str, dict] = {}
    for r in rows:
        plan = r["plan"] or "free"; status = r["status"] or "inactive"
        if plan not in plan_map:
            plan_map[plan] = {"plan": plan, "count": 0, "active": 0, "trialing": 0, "inactive": 0}
        plan_map[plan]["count"] += r["cnt"]
        if status in plan_map[plan]:
            plan_map[plan][status] += r["cnt"]

    for pd in plan_map.values():
        price = PLAN_AMOUNT_GBP.get(pd["plan"], 0)
        pd["mrr"] = round(price * (pd["active"] + pd["trialing"]), 2)

    by_plan = sorted(plan_map.values(), key=lambda x: x["mrr"], reverse=True)
    total_mrr = round(sum(p["mrr"] for p in by_plan), 2)
    return {
        "by_plan": by_plan, "total_mrr": total_mrr, "total_arr": round(total_mrr * 12, 2),
        "total_subscribers": sum(p["count"] for p in by_plan),
        "total_active": sum(p["active"] for p in by_plan),
        "total_trialing": sum(p["trialing"] for p in by_plan),
        "total_in_db": total_row["cnt"] if total_row else 0,
        "recent_subscriptions": [{"email": r["email"], "plan": r["plan"], "status": r["status"], "created_at": r["created_at"], "has_stripe": bool(r["stripe_subscription_id"])} for r in recent],
    }


# ── Helpers ────────────────────────────────────────────────────────────────────
def _upsert_subscription(
    email: str, plan: str, status: str,
    stripe_customer_id: str = "", stripe_subscription_id: str = "",
    stripe_session_id: str = "", current_period_end: Optional[int] = None,
) -> None:
    now = int(time.time())
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM subscriptions WHERE email=?", (email,)).fetchone()
        if existing:
            conn.execute("UPDATE subscriptions SET plan=?,status=?,stripe_customer_id=?,stripe_subscription_id=?,stripe_session_id=?,current_period_end=?,updated_at=? WHERE email=?",
                         (plan, status, stripe_customer_id, stripe_subscription_id, stripe_session_id, current_period_end, now, email))
        else:
            conn.execute("INSERT INTO subscriptions (email,plan,status,stripe_customer_id,stripe_subscription_id,stripe_session_id,current_period_end,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (email, plan, status, stripe_customer_id, stripe_subscription_id, stripe_session_id, current_period_end, now, now))
        conn.commit()

