"""Request-id middleware (nginx-compatible X-Request-Id)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from libs.shared_http.request_id import RequestIdMiddleware, get_request_id


def test_echoes_incoming_x_request_id():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping():
        return {"request_id": get_request_id()}

    client = TestClient(app)
    response = client.get("/ping", headers={"X-Request-Id": "client-trace-99"})
    assert response.status_code == 200
    assert response.json()["request_id"] == "client-trace-99"
    assert response.headers.get("X-Request-Id") == "client-trace-99"


def test_generates_uuid_when_header_absent():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping():
        return {"request_id": get_request_id()}

    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    rid = response.headers.get("X-Request-Id")
    assert rid
    assert len(rid) >= 32
    assert response.json()["request_id"] == rid
