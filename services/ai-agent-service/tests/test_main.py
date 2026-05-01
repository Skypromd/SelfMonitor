import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# --- Patch heavy dependencies before importing app.main ---
mock_memory_manager = MagicMock()
mock_memory_manager.initialize = AsyncMock()
mock_memory_manager.close = AsyncMock()

mock_tool_registry = MagicMock()
mock_tool_registry.discover_services = AsyncMock()

mock_agent = MagicMock()
mock_agent.is_ready.return_value = True
mock_agent.get_uptime_hours.return_value = 0.0

mock_conversation_manager = MagicMock()
mock_conversation_manager.get_active_session_count.return_value = 0
mock_conversation_manager.get_total_conversation_count = AsyncMock(return_value=0)

with (
    patch("app.memory.memory_manager.MemoryManager", return_value=mock_memory_manager),
    patch("app.tools.tool_registry.ToolRegistry", return_value=mock_tool_registry),
    patch("app.agent.conversation_manager.ConversationManager", return_value=mock_conversation_manager),
    patch("app.agent.selfmate_agent.SelfMateAgent", return_value=mock_agent),
):
    from app.main import app

client = TestClient(app)


def make_token(sub: str = "user-abc") -> str:
    payload = {"sub": sub, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


AUTH_HEADER = {"Authorization": f"Bearer {make_token()}"}


def test_health_no_auth():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-agent-service"


def test_status_no_auth():
    resp = client.get("/status")
    assert resp.status_code == 401


def test_chat_no_auth():
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 401


def test_status_with_auth():
    resp = client.get("/status", headers=AUTH_HEADER)
    assert resp.status_code in (200, 503)


def test_chat_with_auth():
    resp = client.post("/chat", headers=AUTH_HEADER, json={"message": "What is my tax?"})
    assert resp.status_code in (200, 503, 500)
