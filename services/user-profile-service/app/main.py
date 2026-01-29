from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
import hashlib
import hmac
import json
import os
import time

from . import crud, models, schemas
from .database import get_db

app = FastAPI(
    title="User Profile Service",
    description="Manages user profile data.",
    version="1.0.0"
)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_PRO_MONTHLY_ID = os.getenv("STRIPE_PRICE_PRO_MONTHLY_ID")
STRIPE_PRICE_PRO_ANNUAL_ID = os.getenv("STRIPE_PRICE_PRO_ANNUAL_ID")


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str, tolerance: int = 300) -> bool:
    try:
        parts = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = int(parts.get("t", "0"))
        signatures = [value for key, value in parts.items() if key == "v1"]
        if not signatures:
            return False
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, signature) for signature in signatures):
            return False
        if abs(time.time() - timestamp) > tolerance:
            return False
        return True
    except Exception:
        return False


def _resolve_plan(price_id: str | None) -> str:
    if price_id and price_id in {STRIPE_PRICE_PRO_MONTHLY_ID, STRIPE_PRICE_PRO_ANNUAL_ID}:
        return "pro"
    return "free"


def _resolve_cycle(interval: str | None) -> str:
    if interval == "year":
        return "annual"
    return "monthly"


def _date_from_unix(value: int | None) -> datetime.date | None:
    if not value:
        return None
    return datetime.datetime.utcfromtimestamp(value).date()

# --- Placeholder Security ---
def fake_auth_check() -> str:
    """A fake dependency to simulate user authentication and return a user ID."""
    return "fake-user-123"

# @app.on_event("startup")
# async def startup():
#     # This logic is now handled by Alembic migrations.
#     # You should run `alembic upgrade head` before starting the application.
#     pass

# --- Endpoints ---
@app.get("/profiles/me", response_model=schemas.UserProfile)
async def get_my_profile(
    user_id: str = Depends(fake_auth_check), 
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the profile for the currently authenticated user from the database."""
    db_profile = await crud.get_profile_by_user_id(db, user_id=user_id)
    if db_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return db_profile

@app.put("/profiles/me", response_model=schemas.UserProfile)
async def create_or_update_my_profile(
    profile_update: schemas.UserProfileUpdate,
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new profile or updates an existing one for the authenticated user in the database."""
    db_profile = await crud.create_or_update_profile(db, user_id=user_id, profile=profile_update)
    return db_profile


@app.get("/subscriptions/me", response_model=schemas.SubscriptionResponse)
async def get_my_subscription(
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    profile = await crud.get_or_create_profile(db, user_id=user_id)
    return profile


@app.put("/subscriptions/me", response_model=schemas.SubscriptionResponse)
async def update_my_subscription(
    update: schemas.SubscriptionUpdate,
    user_id: str = Depends(fake_auth_check),
    db: AsyncSession = Depends(get_db)
):
    profile = await crud.update_subscription(db, user_id=user_id, update=update)
    return profile


@app.post("/billing/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    if STRIPE_WEBHOOK_SECRET:
        if not sig_header or not _verify_stripe_signature(payload, sig_header, STRIPE_WEBHOOK_SECRET):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event = json.loads(payload.decode("utf-8") or "{}")
    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})

    user_id = (
        data_object.get("metadata", {}).get("user_id")
        or data_object.get("client_reference_id")
    )
    if not user_id:
        return {"received": True}

    update_data = {}

    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        price_id = None
        interval = None
        items = data_object.get("items", {}).get("data", [])
        if items:
            price = items[0].get("price", {})
            price_id = price.get("id")
            interval = price.get("recurring", {}).get("interval")
        update_data = {
            "subscription_plan": _resolve_plan(price_id),
            "subscription_status": data_object.get("status", "active"),
            "billing_cycle": _resolve_cycle(interval),
            "current_period_start": _date_from_unix(data_object.get("current_period_start")),
            "current_period_end": _date_from_unix(data_object.get("current_period_end")),
        }
    elif event_type == "customer.subscription.deleted":
        update_data = {
            "subscription_plan": "free",
            "subscription_status": "canceled",
        }
    elif event_type == "checkout.session.completed":
        update_data = {
            "subscription_plan": "pro",
            "subscription_status": data_object.get("status", "active"),
            "billing_cycle": data_object.get("metadata", {}).get("billing_cycle", "monthly"),
        }

    if update_data:
        await crud.update_subscription(db, user_id=user_id, update=schemas.SubscriptionUpdate(**update_data))

    return {"received": True}
