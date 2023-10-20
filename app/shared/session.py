import contextlib
import typing as t
from contextvars import ContextVar
from functools import partial

import aiohttp

__all__ = ("IO_CLIENT", "create_client_session")


IO_CLIENT: ContextVar[aiohttp.ClientSession] = ContextVar("session")
"""The aiohttp.ClientSession available for general use."""


class HTTPClient(t.Protocol):
    connector: aiohttp.BaseConnector | None
    proxy: str | None


@contextlib.asynccontextmanager
async def create_client_session(client: HTTPClient, /) -> t.AsyncIterator[aiohttp.ClientSession]:
    """Context manager establishing a client session, reusing client's connector & proxy."""
    async with aiohttp.ClientSession(
        connector=client.connector, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        session._request = partial(session._request, proxy=client.proxy)
        yield session
