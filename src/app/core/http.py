import logging
from enum import IntEnum
from typing import Any, Final
from typing_extensions import override

import aiohttp
import orjson
from aiohttp.typedefs import StrOrURL

import disnake.http

__all__ = ("ResponseStatus", "client_session")

_LOG = logging.getLogger(__name__)

session: Final[aiohttp.ClientSession]
"""Global HTTP session. Access via `from app.core import http; http.session`"""


class ResponseStatus(IntEnum):
    """A subset of HTTP status codes relevant to this app."""

    ok = 200
    bad_request = 400
    unauthorized = 401
    forbidden = 403
    not_found = 404
    Im_a_teapot = 418


class _ClientSession(aiohttp.ClientSession):
    @override
    async def _request(
        self,
        method: str,
        str_or_url: StrOrURL,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        _LOG.info("Request method=%s url=%s", method, str_or_url)
        response = await super()._request(method, str_or_url, **kwargs)
        _LOG.log(
            logging.INFO if response.status == ResponseStatus.ok else logging.WARNING,
            "Response method=%s url=%s status=%d type=%s length=%s",
            method,
            str_or_url,
            response.status,
            response.content_type,
            response.content_length,
        )
        return response


def client_session(client: disnake.http.HTTPClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""
    global session  # noqa: PLW0603

    def _dumps(obj: object, /) -> str:
        # (Any) -> str which then they encode...
        return orjson.dumps(obj).decode()

    session = _ClientSession(
        connector=client.connector,
        connector_owner=client.connector is None,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    return session
