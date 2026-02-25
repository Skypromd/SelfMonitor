import os
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

DEFAULT_SECRET_KEY = "a_very_secret_key_that_should_be_in_an_env_var"
DEFAULT_ALGORITHM = "HS256"


def build_jwt_auth_dependencies(
    secret_key_env_var: str = "AUTH_SECRET_KEY",
    algorithm: str = DEFAULT_ALGORITHM,
) -> tuple[Callable[..., str], Callable[..., str]]:
    """Create FastAPI dependencies for bearer token extraction and JWT subject decoding."""

    secret_key = os.getenv(secret_key_env_var, DEFAULT_SECRET_KEY)

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
        return user_id

    return get_bearer_token, get_current_user_id

