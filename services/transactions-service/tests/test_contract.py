import asyncio
import datetime
import os
import socket
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
import pytest
import uvicorn
from pact import Verifier
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import models
from app.database import Base, get_db
from app.main import app, get_current_user_id

if os.getenv("ENABLE_CONTRACT_TESTS") != "1":
    pytest.skip(
        "Contract tests are disabled. Set ENABLE_CONTRACT_TESTS=1 to run.",
        allow_module_level=True,
    )

CONSUMER_NAME = "TaxEngineService"
PROVIDER_NAME = "TransactionsService"
PACT_OUTPUT_DIR = Path(os.getenv("PACT_OUTPUT_DIR", Path(tempfile.gettempdir()) / "pacts"))
PACT_FILE = PACT_OUTPUT_DIR / f"{CONSUMER_NAME}-{PROVIDER_NAME}.json"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_provider_ready(base_url: str) -> None:
    for _ in range(50):
        try:
            response = httpx.get(
                f"{base_url}/transactions/me",
                headers={"Authorization": "Bearer fake-token"},
                timeout=0.3,
            )
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Provider server did not become ready in time")


@dataclass
class ProviderRuntime:
    base_url: str
    state_handlers: dict[str, Callable[..., None]]


@pytest.fixture(scope="module")
def provider_runtime():
    db_file = Path(tempfile.gettempdir()) / f"transactions_provider_contract_{uuid.uuid4().hex}.db"
    test_database_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(test_database_url)
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession,
    )

    async def override_get_db():
        async with testing_session_local() as session:
            yield session

    async def override_get_current_user_id():
        return "test_user"

    async def init_db() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def drop_db() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    async def set_state_transactions_exist_for_user() -> None:
        async with testing_session_local() as session:
            await session.execute(delete(models.Transaction))
            session.add(
                models.Transaction(
                    id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
                    account_id=uuid.UUID("123e4567-e89b-12d3-a456-426614174001"),
                    user_id="test_user",
                    provider_transaction_id="txn_abc",
                    date=datetime.date(2023, 10, 10),
                    description="Tesco",
                    amount=123.45,
                    currency="GBP",
                    category="groceries",
                )
            )
            await session.commit()

    def state_transactions_exist_for_user(
        _state: str | None = None,
        _action: str | None = None,
        _parameters: dict | None = None,
    ) -> None:
        asyncio.run(set_state_transactions_exist_for_user())

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    asyncio.run(init_db())

    port = _find_free_port()
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    _wait_for_provider_ready(base_url)

    yield ProviderRuntime(
        base_url=base_url,
        state_handlers={
            "transactions exist for a user": state_transactions_exist_for_user,
        },
    )

    server.should_exit = True
    thread.join(timeout=5)
    app.dependency_overrides.clear()
    asyncio.run(drop_db())
    asyncio.run(engine.dispose())
    if db_file.exists():
        db_file.unlink()


@pytest.mark.skipif(not PACT_FILE.exists(), reason="Pact file not found")
def test_transaction_service_honours_pact_with_tax_engine(provider_runtime: ProviderRuntime):
    verifier = (
        Verifier(PROVIDER_NAME)
        .add_transport(url=provider_runtime.base_url)
        .add_source(PACT_FILE)
        .add_custom_header("Authorization", "Bearer fake-token")
        .state_handler(provider_runtime.state_handlers)
    )

    verifier.verify()
    assert verifier.results

