"""Stripe Payment Links for client invoices (GBP-oriented; verify amounts server-side)."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import stripe

from . import models


def _require_stripe_key() -> str:
    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")
    return key


def create_stripe_payment_link(*, invoice: models.Invoice, user_id: str) -> tuple[str, str]:
    """Returns (payment_link_url, stripe_payment_link_id)."""
    stripe.api_key = _require_stripe_key()
    currency = (invoice.currency or "GBP").lower()
    total = Decimal(str(invoice.total_amount))
    unit_amount = int((total * 100).quantize(Decimal("1")))
    if unit_amount < 1:
        raise ValueError("Invoice total must be at least 0.01 in major currency units")

    inv_id = str(invoice.id)
    link = stripe.PaymentLink.create(
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {"name": f"Invoice {invoice.invoice_number}"},
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }
        ],
        metadata={
            "invoice_id": inv_id,
            "user_id": user_id,
        },
    )
    url = getattr(link, "url", None) or ""
    lid = getattr(link, "id", None) or ""
    if not url or not lid:
        raise RuntimeError("Stripe returned an incomplete PaymentLink")
    return url, lid


def parse_checkout_session_completed(event: dict[str, Any]) -> dict[str, Any] | None:
    if event.get("type") != "checkout.session.completed":
        return None
    data = event.get("data") or {}
    obj = data.get("object") or {}
    if obj.get("payment_status") != "paid":
        return None
    meta = obj.get("metadata") or {}
    invoice_id = meta.get("invoice_id")
    if not invoice_id:
        return None
    amount_total = obj.get("amount_total")
    currency = (obj.get("currency") or "gbp").upper()
    session_id = obj.get("id") or ""
    if not isinstance(amount_total, int) or not session_id:
        return None
    return {
        "invoice_id": str(invoice_id),
        "amount_total_minor": amount_total,
        "currency": currency,
        "checkout_session_id": str(session_id),
    }
