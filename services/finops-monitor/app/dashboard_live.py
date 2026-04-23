from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

log = logging.getLogger(__name__)


def _decode_ws_user_id(token: str, *, secret: str, algorithm: str) -> str:
    t = (token or "").strip()
    if t.startswith("Bearer "):
        t = t[7:]
    if not t:
        raise ValueError("missing_token")
    payload = jwt.decode(t, secret, algorithms=[algorithm])
    sub = payload.get("sub")
    if not sub or "@" not in str(sub):
        raise ValueError("invalid_sub")
    return str(sub).strip().lower()


async def websocket_dashboard_live(
    *,
    websocket: WebSocket,
    redis_client: Any,
    auth_secret_key: str,
    auth_algorithm: str,
) -> None:
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await websocket.close(code=1008, reason="auth_timeout")
        return
    try:
        user_id = _decode_ws_user_id(raw, secret=auth_secret_key, algorithm=auth_algorithm)
    except (JWTError, ValueError):
        await websocket.close(code=1008, reason="unauthorized")
        return

    channel = f"dashboard:live:{user_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    async def heartbeat() -> None:
        try:
            while True:
                await asyncio.sleep(25)
                await websocket.send_json({"type": "ping"})
        except Exception:
            return

    hb = asyncio.create_task(heartbeat())
    try:
        async for msg in pubsub.listen():
            if msg.get("type") == "message":
                await websocket.send_json({"type": "transactions_updated"})
    except WebSocketDisconnect:
        log.info("dashboard ws closed user=%s", user_id)
    except Exception as exc:
        log.warning("dashboard ws error user=%s: %s", user_id, exc)
    finally:
        hb.cancel()
        try:
            await hb
        except asyncio.CancelledError:
            pass
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass


async def publish_dashboard_refresh(redis_client: Any, *, user_id: str) -> int:
    uid = user_id.strip().lower()
    if not uid:
        return 0
    return int(await redis_client.publish(f"dashboard:live:{uid}", "1") or 0)
