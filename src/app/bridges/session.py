from functools import partial
from typing import Protocol

import aiohttp
import orjson

__all__ = ("client_session",)


class HTTPClient(Protocol):
    connector: aiohttp.BaseConnector | None
    proxy: str | None


def client_session(client: HTTPClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""

    def _dumps(obj: object, /) -> str:
        return orjson.dumps(obj).decode()  # it will be encoded again right away but oh well

    session = aiohttp.ClientSession(
        connector=client.connector,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    session._request = partial(session._request, proxy=client.proxy)  # pyright: ignore[reportPrivateUsage]
    return session
