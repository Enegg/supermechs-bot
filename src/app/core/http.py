import io
import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Final, override

import aiohttp
import attrs
import orjson
from aiohttp.typedefs import StrOrURL

import disnake.http

from app.utils import as_binary_unit

__all__ = ("ResponseStatus", "client_session")

_LOG = logging.getLogger("io")

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
            "Response method=%s url=%s status=%d type=%s length=%s (%s%sB)",
            method,
            str_or_url,
            response.status,
            response.content_type,
            response.content_length,
            *as_binary_unit(response.content_length or 0),
        )
        return response


def client_session(client: disnake.http.HTTPClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""
    global session

    # .venv/Lib/site-packages/aiohttp/payload.py:396
    # aiohttp wants dumps(Any) -> str, then encodes it
    @attrs.define
    class _MockStr(str if TYPE_CHECKING else object):
        proxied_bytes: bytes

        @override
        def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
            return self.proxied_bytes

    def _dumps(obj: object, /) -> str:
        return _MockStr(orjson.dumps(obj))

    session = _ClientSession(
        connector=client.connector,
        connector_owner=client.connector is None,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    return session


@attrs.define(auto_exc=True)
class ContentSizeError(OSError):
    max_size: int
    received: int


async def read_content(
    response: aiohttp.ClientResponse, max_size: int | None = None, chunk_size: int = -1
) -> io.BytesIO:
    if max_size is None:
        bio = io.BytesIO(await response.content.read())
        bio.seek(0)
        return bio

    if response.content_length is not None and response.content_length > max_size:
        raise ContentSizeError(max_size, response.content_length)

    bio = io.BytesIO()

    async for chunk in (
        response.content.iter_chunked(chunk_size)
        if chunk_size != -1
        else response.content.iter_any()
    ):
        bio.write(chunk)

        if bio.tell() > max_size:
            raise ContentSizeError(max_size, bio.tell())

    bio.seek(0)
    return bio
