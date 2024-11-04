import logging
from typing import Any, Protocol

import aiohttp
import orjson
from aiohttp.typedefs import StrOrURL

__all__ = ("client_session",)

RESPONSE_OK = 200
_LOG = logging.getLogger(__name__)


class HttpClient(Protocol):
    @property
    def connector(self) -> aiohttp.BaseConnector | None: ...
    @property
    def proxy(self) -> str | None: ...


def client_session(client: HttpClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""

    def _dumps(obj: object, /) -> str:
        # (Any) -> str which then they encode...
        return orjson.dumps(obj).decode()

    session = aiohttp.ClientSession(
        connector=client.connector,
        connector_owner=client.connector is None,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    _request = session._request  # pyright: ignore[reportPrivateUsage]

    async def _log_request(
        method: str,
        str_or_url: StrOrURL,
        **kwargs: Any,  # noqa: ANN401
    ) -> aiohttp.ClientResponse:
        _LOG.info("Request method=%s url=%s", method, str_or_url)
        response = await _request(method, str_or_url, proxy=client.proxy, **kwargs)

        _LOG.log(
            logging.INFO if response.status == RESPONSE_OK else logging.WARNING,
            "Response method=%s url=%s status=%d type=%s length=%s",
            method,
            str_or_url,
            response.status,
            response.content_type,
            response.content_length,
        )
        return response

    session._request = _log_request  # pyright: ignore[reportPrivateUsage]
    return session
