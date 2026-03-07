"""
Billing Service — Stripe payment integration for SelfMonitor
Handles checkout session creation, webhook processing, and subscription management.

Dev mode: if STRIPE_SECRET_KEY is not set, returns a mock checkout URL pointing
directly to the registration page (no actual payment is taken).
"""
import logging
import os
import sqlite3
import time
from typing import Optional

import httpx
import stripe
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:80")
DEV_MODE = not bool(STRIPE_SECRET_KEY)

if not DEV_MODE:
    stripe.api_key = STRIPE_SECRET_KEY

DB_PATH = os.getenv(
    "BILLING_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "billing.db"),
)

# ── Plan definitions ──────────────────────────────────────────────────────────
# Set STRIPE_PRICE_<PLAN> env vars to your real Stripe Price IDs.
# Example: STRIPE_PRICE_STARTER=price_1ABC...
PLANS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "amount": 0,
        "currency": "gbp",
        "interval": None,
        "price_id": os.getenv("STRIPE_PRICE_FREE", ""),
    },
    "starter": {
        "name": "Starter",
        "amount": 900,   # £9.00 in pence
        "currency": "gbp",
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_STARTER", ""),
    },
    "growth": {
        "name": "Growth",
        "amount": 1200,  # £12.00
        "currency": "gbp",
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_GROWTH", ""),
    },
    "pro": {
        "name": "Pro",
        "amount": 1500,  # £15.00
        "currency": "gbp",
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_PRO", ""),
    },
    "business": {
        "name": "Business",
        "amount": 2500,  # £25.00
        "currency": "gbp",
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_BUSINESS", ""),
    },
}

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Billing Service",
    description="Stripe payment integration — checkout sessions, webhooks, subscriptions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

# ── Database ───────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
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
        conn.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()
    if DEV_MODE:
        logger.warning(
            "Billing service running in DEV MODE — no real Stripe payments. "
            "Set STRIPE_SECRET_KEY to enable live payments."
        )


# ── Schemas ────────────────────────────────────────────────────────────────────
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


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dev_mode": DEV_MODE}


@app.get("/plans")
def list_plans() -> dict:
    return {
        key: {
            "name": val["name"],
            "amount": val["amount"],
            "currency": val["currency"],
            "interval": val["interval"],
        }
        for key, val in PLANS.items()
    }


@app.post("/checkout/session", response_model=CheckoutResponse)
async def create_checkout_session(body: CheckoutRequest) -> CheckoutResponse:
    """
    Create a Stripe Checkout session (or a mock in dev mode).
    Returns the URL to redirect the user to for payment.
    """
    plan_key = body.plan.lower()
    plan = PLANS.get(plan_key)
    if plan is None:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    # Free plan — skip payment, go straight to register
    if plan["amount"] == 0:
        register_url = f"{FRONTEND_URL}/register?plan={plan_key}"
        return CheckoutResponse(
            checkout_url=register_url,
            session_id="free",
            dev_mode=DEV_MODE,
        )

    success_url = f"{FRONTEND_URL}/checkout-success?plan={plan_key}&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{FRONTEND_URL}/checkout-cancel?plan={plan_key}"

    # ── Dev mode: no Stripe ────────────────────────────────────────────────────
    if DEV_MODE:
        mock_session_id = f"dev_session_{plan_key}_{int(time.time())}"
        # In dev mode, redirect directly to success page without real payment
        mock_url = (
            f"{FRONTEND_URL}/checkout-success"
            f"?plan={plan_key}&session_id={mock_session_id}&dev=1"
        )
        return CheckoutResponse(
            checkout_url=mock_url,
            session_id=mock_session_id,
            dev_mode=True,
        )

    # ── Live mode: create real Stripe session ──────────────────────────────────
    try:
        params: dict = {
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"plan": plan_key},
            "subscription_data": {
                "trial_period_days": 14,
                "metadata": {"plan": plan_key},
            },
        }

        if plan.get("price_id"):
            params["line_items"] = [{"price": plan["price_id"], "quantity": 1}]
        else:
            # No Price ID configured — create ad-hoc price
            params["line_items"] = [
                {
                    "price_data": {
                        "currency": plan["currency"],
                        "unit_amount": plan["amount"],
                        "recurring": {"interval": plan["interval"]},
                        "product_data": {
                            "name": f"SelfMonitor {plan['name']}",
                            "description": f"SelfMonitor {plan['name']} subscription",
                        },
                    },
                    "quantity": 1,
                }
            ]

        if body.email:
            params["customer_email"] = body.email

        session = stripe.checkout.Session.create(**params)
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
            dev_mode=False,
        )
    except stripe.StripeError as exc:
        logger.error("Stripe error: %s", exc)
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(exc)}") from exc


@app.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
) -> dict:
    """
    Handles Stripe webhook events to update subscription status.
    Configure this URL in your Stripe dashboard:
      https://your-domain.com/api/billing/webhook
    """
    payload = await request.body()

    if STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError as exc:
            raise HTTPException(status_code=400, detail="Invalid signature") from exc
    else:
        # Dev mode — accept without signature
        import json
        try:
            event = json.loads(payload)
        except Exception:
            return {"status": "ignored"}

    event_type = event.get("type") if isinstance(event, dict) else event.type

    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"] if isinstance(event, dict) else event.data.object
        customer_email = session_obj.get("customer_email") or session_obj.get("customer_details", {}).get("email", "")
        plan = session_obj.get("metadata", {}).get("plan", "starter")
        subscription_id = session_obj.get("subscription", "")
        customer_id = session_obj.get("customer", "")
        session_id = session_obj.get("id", "")

        if customer_email:
            _upsert_subscription(
                email=customer_email,
                plan=plan,
                status="trialing" if session_obj.get("subscription") else "active",
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                stripe_session_id=session_id,
            )

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_obj = event["data"]["object"] if isinstance(event, dict) else event.data.object
        status = sub_obj.get("status", "inactive")
        subscription_id = sub_obj.get("id", "")
        period_end = sub_obj.get("current_period_end")

        with get_db() as conn:
            conn.execute(
                "UPDATE subscriptions SET status=?, current_period_end=?, updated_at=? WHERE stripe_subscription_id=?",
                (status, period_end, int(time.time()), subscription_id),
            )
            conn.commit()

    return {"status": "ok"}


@app.get("/subscription/{email}", response_model=SubscriptionInfo)
def get_subscription(email: str) -> SubscriptionInfo:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE email=? ORDER BY updated_at DESC LIMIT 1",
            (email,),
        ).fetchone()
    if not row:
        return SubscriptionInfo(email=email, plan="free", status="none")
    return SubscriptionInfo(
        email=email,
        plan=row["plan"],
        status=row["status"],
        current_period_end=row["current_period_end"],
    )


# ── Admin endpoints ────────────────────────────────────────────────────────────
async def _verify_admin(request: Request) -> bool:
    """Verifies that the Bearer token belongs to an is_admin user via auth-service."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                f"{AUTH_SERVICE_URL}/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 200:
            return bool(resp.json().get("is_admin", False))
    except Exception:
        pass
    return False


@app.get("/admin/stats")
async def admin_stats(request: Request) -> dict:
    """
    Returns aggregate billing/subscription statistics for the admin panel.
    Requires Bearer token of an is_admin user (verified via auth-service).
    """
    if not await _verify_admin(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    with get_db() as conn:
        rows = conn.execute(
            "SELECT plan, status, COUNT(*) as cnt FROM subscriptions GROUP BY plan, status"
        ).fetchall()
        total_row = conn.execute("SELECT COUNT(*) as cnt FROM subscriptions").fetchone()
        recent = conn.execute(
            "SELECT email, plan, status, created_at, stripe_subscription_id FROM subscriptions ORDER BY created_at DESC LIMIT 20"
        ).fetchall()

    # Aggregate by plan
    plan_map: dict[str, dict] = {}
    for r in rows:
        plan = r["plan"] or "free"
        status = r["status"] or "inactive"
        if plan not in plan_map:
            plan_map[plan] = {"plan": plan, "count": 0, "active": 0, "trialing": 0, "inactive": 0}
        plan_map[plan]["count"] += r["cnt"]
        if status in plan_map[plan]:
            plan_map[plan][status] += r["cnt"]

    # Compute MRR
    plan_prices = {p: PLANS[p]["amount"] / 100 for p in PLANS}
    for plan_data in plan_map.values():
        price = plan_prices.get(plan_data["plan"], 0)
        # Count active + trialing as paying
        paying = plan_data["active"] + plan_data["trialing"]
        plan_data["mrr"] = round(price * paying, 2)

    by_plan = sorted(plan_map.values(), key=lambda x: x["mrr"], reverse=True)
    total_mrr = round(sum(p["mrr"] for p in by_plan), 2)
    total_subscribers = sum(p["count"] for p in by_plan)
    total_active = sum(p["active"] for p in by_plan)
    total_trialing = sum(p["trialing"] for p in by_plan)

    recent_list = [
        {
            "email": row["email"],
            "plan": row["plan"],
            "status": row["status"],
            "created_at": row["created_at"],
            "has_stripe": bool(row["stripe_subscription_id"]),
        }
        for row in recent
    ]

    return {
        "by_plan": by_plan,
        "total_mrr": total_mrr,
        "total_arr": round(total_mrr * 12, 2),
        "total_subscribers": total_subscribers,
        "total_active": total_active,
        "total_trialing": total_trialing,
        "total_in_db": total_row["cnt"] if total_row else 0,
        "recent_subscriptions": recent_list,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────
def _upsert_subscription(
    email: str,
    plan: str,
    status: str,
    stripe_customer_id: str = "",
    stripe_subscription_id: str = "",
    stripe_session_id: str = "",
    current_period_end: Optional[int] = None,
) -> None:
    now = int(time.time())
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM subscriptions WHERE email=?", (email,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE subscriptions
                   SET plan=?, status=?, stripe_customer_id=?, stripe_subscription_id=?,
                       stripe_session_id=?, current_period_end=?, updated_at=?
                   WHERE email=?""",
                (plan, status, stripe_customer_id, stripe_subscription_id,
                 stripe_session_id, current_period_end, now, email),
            )
        else:
            conn.execute(
                """INSERT INTO subscriptions
                   (email, plan, status, stripe_customer_id, stripe_subscription_id,
                    stripe_session_id, current_period_end, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (email, plan, status, stripe_customer_id, stripe_subscription_id,
                 stripe_session_id, current_period_end, now, now),
            )
        conn.commit()
