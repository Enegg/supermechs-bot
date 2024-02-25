import contextlib
import typing
from collections import abc
from contextvars import ContextVar
from functools import partial

import aiohttp

__all__ = ("IO_SESSION", "create_io_session")


IO_SESSION = ContextVar[aiohttp.ClientSession]("io_session")
"""The aiohttp.ClientSession available for general use."""


class HTTPClient(typing.Protocol):
    connector: aiohttp.BaseConnector | None
    proxy: str | None


@contextlib.asynccontextmanager
async def create_io_session(client: HTTPClient, /) -> abc.AsyncIterator[aiohttp.ClientSession]:
    """Context manager establishing a client session, reusing client's connector & proxy."""
    async with aiohttp.ClientSession(
        connector=client.connector, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        session._request = partial(session._request, proxy=client.proxy)
        yield session
