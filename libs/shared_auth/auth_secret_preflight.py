"""Fail-fast validation for JWT signing secrets used across services."""

from __future__ import annotations

import os


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def resolve_auth_secret_key(*, env_var: str = "AUTH_SECRET_KEY") -> str:
    """
    Read secret from the environment (no default). Enforce minimum length in
    production-like mode unless AUTH_ALLOW_WEAK_JWT_SECRET is set (same escape
    hatch as auth-service config).
    """
    try:
        raw = os.environ[env_var].strip()
    except KeyError as exc:
        raise RuntimeError(f"{env_var} must be set") from exc
    if not raw:
        raise RuntimeError(f"{env_var} must be non-empty")
    allow_weak = _truthy_env("AUTH_ALLOW_WEAK_JWT_SECRET")
    strict = _truthy_env("AUTH_SECRET_KEY_PREFLIGHT_STRICT")
    profile = (os.getenv("DEPLOYMENT_PROFILE") or os.getenv("APP_ENV") or "").strip().lower()
    prod_like = strict or profile in ("production", "prod")
    if prod_like and not allow_weak and len(raw) < 32:
        raise RuntimeError(
            f"{env_var} must be at least 32 characters when "
            "DEPLOYMENT_PROFILE or APP_ENV is production/prod, or AUTH_SECRET_KEY_PREFLIGHT_STRICT=1. "
            "For local dev or CI set AUTH_ALLOW_WEAK_JWT_SECRET=1."
        )
    return raw
