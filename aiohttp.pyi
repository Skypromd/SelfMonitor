# Type stubs for aiohttp (minimal)
from typing import Any, Optional, Mapping, AsyncContextManager
from types import TracebackType

class ClientResponse:
    status: int
    async def json(self) -> Any: ...
    async def text(self) -> str: ...
    async def read(self) -> bytes: ...

class ClientSession:
    def __init__(self, **kwargs: Any) -> None: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> "ClientSession": ...
    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None: ...
    
    def get(
        self,
        url: str,
        **kwargs: Any
    ) -> AsyncContextManager[ClientResponse]: ...
    
    def post(
        self,
        url: str,
        *,
        data: Any = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        **kwargs: Any
    ) -> AsyncContextManager[ClientResponse]: ...
    
    def put(
        self,
        url: str,
        **kwargs: Any
    ) -> AsyncContextManager[ClientResponse]: ...
    
    def delete(
        self,
        url: str,
        **kwargs: Any
    ) -> AsyncContextManager[ClientResponse]: ...

class ClientError(Exception): ...
class ClientConnectionError(ClientError): ...
