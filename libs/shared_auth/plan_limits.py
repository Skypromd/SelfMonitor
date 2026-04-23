"""
Subscription limits from JWT claims (issued by auth-service).

Use for fast enforcement on each request. Claims are refreshed when the client calls
``POST /token/refresh`` (refresh token) or logs in again — those paths rebuild claims from DB.

For authoritative plan state in edge cases, call auth ``GET /subscription/me`` (requires access token).
Fallbacks match free-tier defaults when tokens predate a claim.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

from .auth_secret_preflight import resolve_auth_secret_key
from .jwt_fastapi import build_jwt_auth_dependencies

_get_bearer_token, _ = build_jwt_auth_dependencies()

_DEFAULT_FREE = {
    "plan": "free",
    "bank_connections_limit": 1,
    "bank_sync_daily_limit": 0,
    "transactions_per_month_limit": 20,
    "storage_limit_gb": 1,
    "transaction_history_months": 3,
    "hmrc_direct_submission": False,
    "vat_returns": False,
    "mortgage_reports": False,
    "advanced_analytics": False,
    "cash_flow_forecast": False,
}

# Fallback when JWT omits bank_connections_limit (align with auth-service PLAN_FEATURES).
_BANK_CONNECTIONS_BY_PLAN: dict[str, int] = {
    "free": 1,
    "starter": 3,
    "growth": 2,
    "pro": 5,
    "business": 10,
}

# Fallback when JWT omits transactions_per_month_limit (align with auth-service PLAN_FEATURES).
_TRANSACTIONS_PER_MONTH_BY_PLAN: dict[str, int] = {
    "free": 20,
    "starter": 999999,
    "growth": 2000,
    "pro": 5000,
    "business": 999999,
}

# Fallback when JWT predates bank_sync_daily_limit claim (align with auth-service PLAN_FEATURES).
_BANK_SYNC_DAILY_BY_PLAN: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "growth": 3,
    "pro": 10,
    "business": 25,
}

_TRANSACTION_HISTORY_MONTHS_BY_PLAN: dict[str, int] = {
    "free": 3,
    "starter": 3,
    "growth": 12,
    "pro": 24,
    "business": 36,
}

_HMRC_DIRECT_BY_PLAN: dict[str, bool] = {
    "free": False,
    "starter": False,
    "growth": False,
    "pro": True,
    "business": True,
}

_VAT_RETURNS_BY_PLAN: dict[str, bool] = {
    "free": False,
    "starter": False,
    "growth": False,
    "pro": True,
    "business": True,
}

_DOCUMENTS_MAX_BY_PLAN: dict[str, int] = {
    "free": 20,
    "starter": 100,
    "growth": 500,
    "pro": 5000,
    "business": 50000,
}

_EVIDENCE_PACK_TIER_BY_PLAN: dict[str, str] = {
    "free": "none",
    "starter": "none",
    "growth": "basic",
    "pro": "full",
    "business": "full",
}

_ACCOUNTANT_REVIEW_CREDITS_BY_PLAN: dict[str, int] = {
    "free": 0,
    "starter": 0,
    "growth": 0,
    "pro": 1,
    "business": 4,
}

# When JWT omits feature booleans (older tokens), infer from plan — keep in sync with auth-service PLAN_FEATURES.
_PLAN_FEATURE_DEFAULTS: dict[str, dict[str, bool]] = {
    "free": {"mortgage_reports": False, "advanced_analytics": False, "cash_flow_forecast": False},
    "starter": {"mortgage_reports": False, "advanced_analytics": False, "cash_flow_forecast": True},
    "growth": {"mortgage_reports": False, "advanced_analytics": False, "cash_flow_forecast": True},
    "pro": {"mortgage_reports": True, "advanced_analytics": True, "cash_flow_forecast": True},
    "business": {"mortgage_reports": True, "advanced_analytics": True, "cash_flow_forecast": True},
}


@dataclass(frozen=True)
class PlanLimits:
    plan: str
    bank_connections_limit: int
    bank_sync_daily_limit: int
    transactions_per_month_limit: int
    storage_limit_gb: int
    transaction_history_months: int = 3
    hmrc_direct_submission: bool = False
    vat_returns: bool = False
    mortgage_reports: bool = False
    advanced_analytics: bool = False
    cash_flow_forecast: bool = False
    documents_max_count: int = 20
    evidence_pack_tier: str = "none"
    accountant_review_credits_per_month: int = 0


def _secret_and_algo() -> tuple[str, str]:
    return resolve_auth_secret_key(), "HS256"


def _int_claim(payload: dict[str, Any], key: str, default: int) -> int:
    raw = payload.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _bool_claim(payload: dict[str, Any], key: str, default: bool) -> bool:
    raw = payload.get(key)
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw)


def _evidence_tier(raw: Any, fallback: str) -> str:
    if raw is None or raw == "":
        return fallback
    s = str(raw).strip().lower()
    if s in {"none", "basic", "full"}:
        return s
    return fallback


def plan_limits_from_payload(payload: dict[str, Any]) -> PlanLimits:
    plan = str(payload.get("plan") or _DEFAULT_FREE["plan"])
    inferred = _PLAN_FEATURE_DEFAULTS.get(plan, _PLAN_FEATURE_DEFAULTS["free"])

    def _feature_bool(key: str) -> bool:
        if key in payload:
            return _bool_claim(payload, key, inferred[key])
        return inferred[key]

    sync_fallback = _BANK_SYNC_DAILY_BY_PLAN.get(plan, _DEFAULT_FREE["bank_sync_daily_limit"])
    hist_fallback = _TRANSACTION_HISTORY_MONTHS_BY_PLAN.get(plan, _DEFAULT_FREE["transaction_history_months"])
    hmrc_dir_fallback = _HMRC_DIRECT_BY_PLAN.get(plan, _DEFAULT_FREE["hmrc_direct_submission"])
    vat_fallback = _VAT_RETURNS_BY_PLAN.get(plan, _DEFAULT_FREE["vat_returns"])
    hmrc_direct = _bool_claim(payload, "hmrc_direct_submission", hmrc_dir_fallback)
    vat_ret = _bool_claim(payload, "vat_returns", vat_fallback)
    doc_cap_fallback = _DOCUMENTS_MAX_BY_PLAN.get(plan, _DOCUMENTS_MAX_BY_PLAN["free"])
    tier_fallback = _EVIDENCE_PACK_TIER_BY_PLAN.get(plan, "none")
    credits_fallback = _ACCOUNTANT_REVIEW_CREDITS_BY_PLAN.get(plan, 0)
    bank_conn_fallback = _BANK_CONNECTIONS_BY_PLAN.get(plan, _DEFAULT_FREE["bank_connections_limit"])
    tx_per_mo_fallback = _TRANSACTIONS_PER_MONTH_BY_PLAN.get(
        plan, _DEFAULT_FREE["transactions_per_month_limit"]
    )
    return PlanLimits(
        plan=plan,
        bank_connections_limit=_int_claim(payload, "bank_connections_limit", bank_conn_fallback),
        bank_sync_daily_limit=_int_claim(payload, "bank_sync_daily_limit", sync_fallback),
        transactions_per_month_limit=_int_claim(
            payload,
            "transactions_per_month_limit",
            tx_per_mo_fallback,
        ),
        storage_limit_gb=_int_claim(payload, "storage_limit_gb", _DEFAULT_FREE["storage_limit_gb"]),
        transaction_history_months=_int_claim(payload, "transaction_history_months", hist_fallback),
        hmrc_direct_submission=hmrc_direct,
        vat_returns=vat_ret,
        mortgage_reports=_feature_bool("mortgage_reports"),
        advanced_analytics=_feature_bool("advanced_analytics"),
        cash_flow_forecast=_feature_bool("cash_flow_forecast"),
        documents_max_count=max(0, _int_claim(payload, "documents_max_count", doc_cap_fallback)),
        evidence_pack_tier=_evidence_tier(payload.get("evidence_pack_tier"), tier_fallback),
        accountant_review_credits_per_month=max(
            0, _int_claim(payload, "accountant_review_credits_per_month", credits_fallback)
        ),
    )


def strict_hmrc_fraud_client_context_required_from_payload(payload: dict[str, Any]) -> bool:
    """
    Pro/Business (hmrc_direct_submission) must supply full hmrc_fraud client_context when using live HMRC.
    Starter/Growth omit the claim or set hmrc_direct_submission=false — validation stays lenient.
    """
    if payload.get("type") == "refresh":
        return False
    if "hmrc_direct_submission" in payload:
        return payload.get("hmrc_direct_submission") is True
    plan = str(payload.get("plan") or "free")
    return _HMRC_DIRECT_BY_PLAN.get(plan, False)


def strict_hmrc_fraud_client_context_required(token: str) -> bool:
    secret, algorithm = _secret_and_algo()
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        return False
    return strict_hmrc_fraud_client_context_required_from_payload(payload)


def try_plan_limits_from_token(token: str) -> PlanLimits | None:
    """Decode limits without raising (for middleware); invalid token → None."""
    secret, algorithm = _secret_and_algo()
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        return None
    return plan_limits_from_payload(payload)


def decode_plan_limits_from_token(token: str) -> PlanLimits:
    secret, algorithm = _secret_and_algo()
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc
    return plan_limits_from_payload(payload)


async def get_plan_limits(token: str = Depends(_get_bearer_token)) -> PlanLimits:
    """FastAPI dependency: subscription limits from JWT (auth-service)."""
    return decode_plan_limits_from_token(token)
