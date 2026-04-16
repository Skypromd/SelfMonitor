import os
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

DEFAULT_ALGORITHM = "HS256"


def build_jwt_auth_dependencies(
    secret_key_env_var: str = "AUTH_SECRET_KEY",
    algorithm: str = DEFAULT_ALGORITHM,
) -> tuple[Callable[..., str], Callable[..., str]]:
    """Create FastAPI dependencies for bearer token extraction and JWT subject decoding."""

    secret_key = os.environ[secret_key_env_var].strip()
    if not secret_key:
        raise RuntimeError(f"{secret_key_env_var} must be non-empty")

    def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
            )
        return authorization.split(" ", 1)[1]

    def get_current_user_id(token: str = Depends(get_bearer_token)) -> str:
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        if payload.get("internal_call") is True:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        return user_id

    return get_bearer_token, get_current_user_id


def build_admin_require_dependency(
    secret_key_env_var: str = "AUTH_SECRET_KEY",
    algorithm: str = DEFAULT_ALGORITHM,
    required_permission: str | None = None,
) -> Callable[..., dict]:
    """SEC.3 — Return a FastAPI dependency that enforces admin/permission check."""
    secret_key = os.environ[secret_key_env_var].strip()
    if not secret_key:
        raise RuntimeError(f"{secret_key_env_var} must be non-empty")

    def _check(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
            )
        token = authorization.split(" ", 1)[1]
        try:
            payload: dict = jwt.decode(token, secret_key, algorithms=[algorithm])
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc
        is_admin = payload.get("is_admin") is True
        role = str(payload.get("role") or "user")
        perms: set[str] = set(payload.get("perms") or [])

        if is_admin or "*" in perms or role in ("owner", "admin"):
            return payload
        if required_permission and required_permission in perms:
            return payload
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: admin or {required_permission or 'admin role'}",
        )

    return _check

