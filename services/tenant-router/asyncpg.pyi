# Comprehensive asyncpg type stubs
from typing import Any, Optional, Union, List, Callable, Awaitable, TypeVar, AsyncContextManager

_T = TypeVar('_T')

class Connection:
    async def execute(self, query: str, *args: Any, timeout: Optional[float] = None) -> str: ...
    async def executemany(self, command: str, args: List[Any]) -> None: ...
    async def fetch(self, query: str, *args: Any, timeout: Optional[float] = None) -> List[Any]: ...
    async def fetchrow(self, query: str, *args: Any, timeout: Optional[float] = None) -> Optional[Any]: ...
    async def fetchval(self, query: str, *args: Any, timeout: Optional[float] = None) -> Any: ...
    async def close(self) -> None: ...

class Pool:
    def acquire(self, *, timeout: Optional[float] = None) -> AsyncContextManager[Connection]: ...
    async def close(self) -> None: ...

async def create_pool(
    dsn: Optional[str] = None,
    *,
    host: Optional[Union[str, List[str]]] = None,
    port: Optional[Union[int, List[int]]] = None,
    user: Optional[str] = None,
    password: Optional[Union[str, Callable[[], str]]] = None,
    database: Optional[str] = None,
    min_size: int = 10,
    max_size: int = 10,
    max_queries: int = 50000,
    max_inactive_connection_lifetime: float = 300.0,
    setup: Optional[Callable[[Connection], Awaitable[None]]] = None,
    init: Optional[Callable[[Connection], Awaitable[None]]] = None,
    connection_class: Optional[Any] = None,
    **kwargs: Any,
) -> Pool: ...

async def connect(
    dsn: Optional[str] = None,
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None, 
    password: Optional[Union[str, Callable[[], str]]] = None,
    database: Optional[str] = None,
    timeout: int = 60,
    **kwargs: Any,
) -> Connection: ...