import http
import io
import logging
import pathlib
from typing import Any, Final

import aiohttp
import anyio
import anyio.to_thread
import attrs
import orjson
import yarl
from monads.result import Err, Ok, Result

import disnake.http

from app.core import CONFIG
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


async def read_path(path: Pathish, /) -> bytes:
    path = pathlib.Path(path)
    _LOG.info("Open path=%s", path)
    return await anyio.to_thread.run_sync(path.read_bytes)


async def read_file(resource: FileResource, /) -> Result[bytes, OSError]:
    try:
        return Ok(await read_path(resource.path))

    except OSError as exc:
        return Err(exc)


def _log_request(url: yarl.URL, method: http.HTTPMethod) -> None:
    _LOG.info("Request method=%s url=%s", method, url)


def _log_response(response: aiohttp.ClientResponse, /) -> None:
    _LOG.log(
        logging.INFO if response.status == http.HTTPStatus.OK else logging.WARNING,
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
    status: int


async def read_http(resource: HttpResource, /) -> Result[bytes, HttpReadError]:
    _log_request(resource.url, http.HTTPMethod.GET)

    async with session.get(resource.url) as response:
        _log_response(response)

        if response.status != http.HTTPStatus.OK:
            return Err(ResponseNotOk(response.status))

        try:
            content = await response.content.read()

        except aiohttp.ClientError as exc:
            return Err(exc)

    return Ok(content)


async def read_user_http(
    resource: HttpResource,
    /,
    max_size: int = CONFIG.max_image_size,
    chunk_size: int = CONFIG.chunk_size,
) -> Result[io.BytesIO, UserHttpReadError]:
    _log_request(resource.url, http.HTTPMethod.GET)

    async with session.get(resource.url) as response:
        _log_response(response)

        if response.status != http.HTTPStatus.OK:
            return Err(ResponseNotOk(response.status))

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
            return await read_file(resource)

        case HttpResource():
            return await read_http(resource)


async def read_user_resource(resource: HttpResource, /) -> Result[io.BytesIO, UserHttpReadError]:
    return await read_user_http(resource)
