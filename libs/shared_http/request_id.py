"""Propagate X-Request-Id through FastAPI (align with nginx map $http_x_request_id)."""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "http_request_id", default=None
)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Use incoming X-Request-Id or generate one; echo on the response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("x-request-id") or request.headers.get(
            "x-requestid"
        )
        rid = (incoming or "").strip() or str(uuid.uuid4())
        token = _request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = rid
            return response
        finally:
            _request_id_ctx.reset(token)
