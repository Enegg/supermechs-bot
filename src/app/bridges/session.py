import logging
from typing import Any, Protocol

import aiohttp
import orjson
from aiohttp.typedefs import StrOrURL

__all__ = ("client_session",)

_LOG = logging.getLogger(__name__)


class HttpClient(Protocol):
    connector: aiohttp.BaseConnector | None
    proxy: str | None


def client_session(client: HttpClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""

    def _dumps(obj: object, /) -> str:
        return orjson.dumps(obj).decode()  # it will be encoded again right away but oh well

    session = aiohttp.ClientSession(
        connector=client.connector,
        connector_owner=client.connector is None,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    _request = session._request  # pyright: ignore[reportPrivateUsage]

    def _log_request(method: str, str_or_url: StrOrURL, **kwargs: Any) -> Any:  # noqa: ANN401
        _LOG.info("method=%s url=%s", method, str_or_url)
        return _request(method, str_or_url, proxy=client.proxy, **kwargs)

    session._request = _log_request  # pyright: ignore[reportPrivateUsage]
    return session
