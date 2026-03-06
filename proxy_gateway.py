"""
Simple API Gateway proxy — replaces nginx for local development without Docker.
Listens on port 8000 and routes /api/<service>/ to the correct local port.
"""

import sys

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dev API Gateway", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route prefix → upstream base URL (mirrors nginx.conf)
ROUTES = {
    "/api/auth/": "http://localhost:8001",
    "/api/token": "http://localhost:8001",
    "/api/profile/": "http://localhost:8005",
    "/api/documents/": "http://localhost:8006",
    "/api/analytics/": "http://localhost:8009",
    "/api/advice/": "http://localhost:8010",
    "/api/localization/": "http://localhost:8012",
    "/api/support/": "http://localhost:8020",
    "/api/partners/": "http://localhost:8016",
    "/api/transactions/": "http://localhost:8003",
    "/api/tax/": "http://localhost:8007",
    "/api/qna/": "http://localhost:8011",
    "/api/calendar/": "http://localhost:8018",
    "/api/agent/": "http://localhost:8019",
}


def resolve_upstream(path: str):
    """Find the upstream URL for a given request path."""
    # Exact match first (e.g. /api/token)
    if path in ROUTES:
        return ROUTES[path], path
    # Prefix match — longest prefix wins
    best_prefix = None
    for route_prefix in ROUTES:
        if path.startswith(route_prefix):
            if best_prefix is None or len(route_prefix) > len(best_prefix):
                best_prefix = route_prefix
    if best_prefix:
        # Strip the /api/<service> prefix, keep the rest
        # e.g. /api/auth/users → /users
        stripped = "/" + path[len(best_prefix) :]
        return ROUTES[best_prefix], stripped
    return None, path


@app.get("/health")
async def health():
    return {"status": "API Gateway running (dev proxy)"}


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
)
async def proxy(path: str, request: Request):
    full_path = "/" + path
    upstream_base, upstream_path = resolve_upstream(full_path)

    if upstream_base is None:
        return Response(content=f"No upstream for path: {full_path}", status_code=502)

    # Preserve query string
    qs = request.url.query
    upstream_url = upstream_base + upstream_path
    if qs:
        upstream_url += "?" + qs

    # Forward headers (strip host)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["x-forwarded-for"] = request.client.host if request.client else "unknown"

    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
        except httpx.ConnectError:
            return Response(
                content=f'{{"error":"Upstream service unavailable: {upstream_base}"}}',
                status_code=503,
                media_type="application/json",
            )


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"Starting dev gateway on 0.0.0.0:{port}")
    print("Routes:")
    for prefix, upstream in ROUTES.items():  # pylint: disable=redefined-outer-name
        print(f"  {prefix:30s} -> {upstream}")
    uvicorn.run(app, host="0.0.0.0", port=port)
