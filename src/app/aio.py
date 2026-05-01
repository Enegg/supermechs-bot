import io
import logging
import pathlib
from http import HTTPMethod as HTTPMethod, HTTPStatus as HTTPStatus
from typing import Any, Final, Self

import aiohttp
import anyio
import anyio.to_thread
import attrs
import orjson
import yarl
from monads.result import Err, Ok, Result

import disnake.http

from app.typeshed import Pathish
from app.utils import as_binary_unit
from resources import AnyResource, FileResource, HttpResource

_LOG = logging.getLogger("io")

session: Final[aiohttp.ClientSession]
"""Global HTTP session. Access via `from app import aio; aio.session`"""

type HttpReadError = aiohttp.ClientError | ResponseNotOk
type UserHttpReadError = HttpReadError | ContentTooLarge


def client_session(client: disnake.http.HTTPClient, /) -> aiohttp.ClientSession:
    """Create a client session with client's connector & proxy."""
    global session

    # .venv/Lib/site-packages/aiohttp/payload.py:396
    # aiohttp wants dumps(Any) -> str, then encodes it
    @attrs.define
    class _MockStr:
        proxied_bytes: bytes

        def encode(self, encoding: str = "", errors: str = "") -> bytes:
            return self.proxied_bytes

    def _dumps(obj: object, /) -> Any:
        return _MockStr(orjson.dumps(obj))

    session = aiohttp.ClientSession(
        connector=client.connector,
        connector_owner=client.connector is None,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )
    return session


async def read_path(path: Pathish, /) -> Result[bytes, OSError]:
    path = pathlib.Path(path)
    _LOG.info("Open path=%s", path)

    try:
        return Ok(await anyio.to_thread.run_sync(path.read_bytes))

    except OSError as exc:
        return Err(exc)


def _log_request(url: yarl.URL, method: HTTPMethod) -> None:
    _LOG.info("Request method=%s url=%s", method, url)


def _log_response(response: aiohttp.ClientResponse, /) -> None:
    _LOG.log(
        logging.INFO if response.status == HTTPStatus.OK else logging.WARNING,
        "Response method=%s url=%s status=%d type=%s length=%s (%s%sB)",
        response.method,
        response.url,
        response.status,
        response.content_type,
        response.content_length,
        *as_binary_unit(response.content_length or 0),
    )


@attrs.define(auto_exc=True)
class ContentTooLarge(OSError):
    received: int
    max_size: int


@attrs.define(auto_exc=True)
class ResponseNotOk(OSError):
    status: HTTPStatus

    @classmethod
    def from_response(cls, response: aiohttp.ClientResponse, /) -> Self:
        return cls(HTTPStatus(response.status))


async def read_http(url: yarl.URL, /) -> Result[bytes, HttpReadError]:
    _log_request(url, HTTPMethod.GET)

    async with session.get(url) as response:
        _log_response(response)

        if response.status != HTTPStatus.OK:
            return Err(ResponseNotOk.from_response(response))

        try:
            content = await response.content.read()

        except aiohttp.ClientError as exc:
            return Err(exc)

    return Ok(content)


async def read_user_http(
    url: yarl.URL,
    /,
    max_size: int = 25 * 1024 * 1024,
    chunk_size: int = 1024 * 1024,
) -> Result[io.BytesIO, UserHttpReadError]:
    _log_request(url, HTTPMethod.GET)

    async with session.get(url) as response:
        _log_response(response)

        if response.status != HTTPStatus.OK:
            return Err(ResponseNotOk.from_response(response))

        if response.content_length is not None and response.content_length > max_size:
            return Err(ContentTooLarge(response.content_length, max_size))

        bio = io.BytesIO()

        async for chunk in response.content.iter_chunked(chunk_size):
            bio.write(chunk)

            if bio.tell() > max_size:
                return Err(ContentTooLarge(bio.tell(), max_size))

    bio.seek(0)
    return Ok(bio)


async def read_resource(resource: AnyResource, /) -> Result[bytes, HttpReadError | OSError]:
    match resource:
        case FileResource():
            return await read_path(resource.path)

        case HttpResource():
            return await read_http(resource.url)


async def read_user_resource(resource: HttpResource, /) -> Result[io.BytesIO, UserHttpReadError]:
    return await read_user_http(resource.url)
