import typing
from contextvars import ContextVar
from functools import partial

import aiohttp
import orjson

__all__ = ("IO_SESSION", "client_session")


IO_SESSION = ContextVar[aiohttp.ClientSession]("io_session")
"""The aiohttp.ClientSession available for general use."""


class HTTPClient(typing.Protocol):
    connector: aiohttp.BaseConnector | None
    proxy: str | None


def _dumps(obj: object, /) -> str:
    return orjson.dumps(obj).decode()  # it will be encoded again right away but oh well


def client_session(client: HTTPClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""
    session = aiohttp.ClientSession(
        connector=client.connector,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    session._request = partial(session._request, proxy=client.proxy)  # pyright: ignore[reportPrivateUsage]
    return session
