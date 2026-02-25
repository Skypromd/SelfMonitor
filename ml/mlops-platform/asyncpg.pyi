# Type stubs for asyncpg - basic interface to resolve type checker errors

from typing import Any, Optional, Union, List, Callable, Awaitable
from typing_extensions import TypeAlias

Connection: TypeAlias = Any
Pool: TypeAlias = Any 
Record: TypeAlias = Any
PoolAcquireContext: TypeAlias = Any

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
    loop: Any = None,
    connection_class: Any = None,
    record_class: Any = None,
    **connect_kwargs: Any,
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