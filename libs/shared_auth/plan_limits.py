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

from .jwt_fastapi import build_jwt_auth_dependencies

_get_bearer_token, _ = build_jwt_auth_dependencies()

_DEFAULT_FREE = {
    "plan": "free",
    "bank_connections_limit": 1,
    "bank_sync_daily_limit": 0,
    "transactions_per_month_limit": 200,
    "storage_limit_gb": 1,
    "mortgage_reports": False,
    "advanced_analytics": False,
    "cash_flow_forecast": False,
}

# Fallback when JWT predates bank_sync_daily_limit claim (align with BANK_SYNC_ECONOMICS.md).
_BANK_SYNC_DAILY_BY_PLAN: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "growth": 2,
    "pro": 3,
    "business": 3,
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
    mortgage_reports: bool = False
    advanced_analytics: bool = False
    cash_flow_forecast: bool = False


def _secret_and_algo() -> tuple[str, str]:
    secret = os.environ["AUTH_SECRET_KEY"].strip()
    if not secret:
        raise RuntimeError("AUTH_SECRET_KEY must be non-empty")
    return secret, "HS256"


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


def plan_limits_from_payload(payload: dict[str, Any]) -> PlanLimits:
    plan = str(payload.get("plan") or _DEFAULT_FREE["plan"])
    inferred = _PLAN_FEATURE_DEFAULTS.get(plan, _PLAN_FEATURE_DEFAULTS["free"])

    def _feature_bool(key: str) -> bool:
        if key in payload:
            return _bool_claim(payload, key, inferred[key])
        return inferred[key]

    sync_fallback = _BANK_SYNC_DAILY_BY_PLAN.get(plan, _DEFAULT_FREE["bank_sync_daily_limit"])
    return PlanLimits(
        plan=plan,
        bank_connections_limit=_int_claim(payload, "bank_connections_limit", _DEFAULT_FREE["bank_connections_limit"]),
        bank_sync_daily_limit=_int_claim(payload, "bank_sync_daily_limit", sync_fallback),
        transactions_per_month_limit=_int_claim(
            payload,
            "transactions_per_month_limit",
            _DEFAULT_FREE["transactions_per_month_limit"],
        ),
        storage_limit_gb=_int_claim(payload, "storage_limit_gb", _DEFAULT_FREE["storage_limit_gb"]),
        mortgage_reports=_feature_bool("mortgage_reports"),
        advanced_analytics=_feature_bool("advanced_analytics"),
        cash_flow_forecast=_feature_bool("cash_flow_forecast"),
    )


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
