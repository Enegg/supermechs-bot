import typing
from contextvars import ContextVar
from functools import partial

import aiohttp

__all__ = ("IO_SESSION", "create_io_session")


IO_SESSION = ContextVar[aiohttp.ClientSession]("io_session")
"""The aiohttp.ClientSession available for general use."""


class HTTPClient(typing.Protocol):
    connector: aiohttp.BaseConnector | None
    proxy: str | None


def create_io_session(client: HTTPClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""
    session = aiohttp.ClientSession(
        connector=client.connector, timeout=aiohttp.ClientTimeout(total=30)
    )
    session._request = partial(session._request, proxy=client.proxy)
    return session
