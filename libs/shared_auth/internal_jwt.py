"""Service-to-service JWTs (separate secret from user access tokens)."""

from __future__ import annotations

import datetime
import os
from typing import Callable, FrozenSet

from jose import JWTError, jwt

SCOPE_RECEIPT_DRAFT_CREATE = "transactions:receipt_drafts:create"
DEFAULT_INTERNAL_AUDIENCE = "mynettax-internal"


class InternalTokenError(Exception):
    """Token is not a valid internal service token for the checked operation."""


def _internal_secret_stripped() -> str:
    secret = os.environ["INTERNAL_SERVICE_SECRET"].strip()
    if not secret:
        raise RuntimeError("INTERNAL_SERVICE_SECRET must be non-empty")
    return secret


def _internal_audience() -> str:
    raw = os.getenv("INTERNAL_JWT_AUDIENCE", DEFAULT_INTERNAL_AUDIENCE)
    aud = (raw or DEFAULT_INTERNAL_AUDIENCE).strip() or DEFAULT_INTERNAL_AUDIENCE
    return aud


def _allowed_internal_issuers() -> FrozenSet[str]:
    raw = os.getenv("INTERNAL_ALLOWED_ISSUERS", "documents-service")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def encode_receipt_draft_internal_token(
    *,
    user_id: str,
    issuer: str,
    ttl_seconds: int = 300,
) -> str:
    secret = _internal_secret_stripped()
    audience = _internal_audience()
    now = int(datetime.datetime.now(datetime.UTC).timestamp())
    payload = {
        "sub": user_id,
        "internal_call": True,
        "iss": issuer,
        "aud": audience,
        "scp": SCOPE_RECEIPT_DRAFT_CREATE,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_receipt_draft_internal_token(token: str) -> str:
    try:
        payload: dict = jwt.decode(
            token,
            _internal_secret_stripped(),
            algorithms=["HS256"],
            audience=_internal_audience(),
            options={"require_exp": True},
        )
    except JWTError as exc:
        raise InternalTokenError from exc
    if payload.get("internal_call") is not True:
        raise InternalTokenError
    if payload.get("scp") != SCOPE_RECEIPT_DRAFT_CREATE:
        raise InternalTokenError
    iss = payload.get("iss")
    if iss not in _allowed_internal_issuers():
        raise InternalTokenError
    sub = payload.get("sub")
    if not sub:
        raise InternalTokenError
    return str(sub)


def build_receipt_draft_create_user_id_dependency() -> Callable[..., str]:
    from fastapi import Depends, Header, HTTPException, status

    auth_secret = os.environ["AUTH_SECRET_KEY"].strip()
    if not auth_secret:
        raise RuntimeError("AUTH_SECRET_KEY must be non-empty")

    def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
            )
        return authorization.split(" ", 1)[1]

    def get_user_id_for_receipt_draft_create(
        token: str = Depends(get_bearer_token),
    ) -> str:
        try:
            return verify_receipt_draft_internal_token(token)
        except InternalTokenError:
            pass
        try:
            user_payload: dict = jwt.decode(
                token, auth_secret, algorithms=["HS256"]
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc
        if user_payload.get("internal_call") is True:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        sub = user_payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        return str(sub)

    return get_user_id_for_receipt_draft_create
