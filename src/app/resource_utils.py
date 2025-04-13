import io
import logging

import aiohttp
import anyio
import attrs
from monads.result import Err, Ok, Result

from app.core import http
from resources import FileResource, HttpResource, Resource

_LOG = logging.getLogger("io")


class UnknownResourceError(NotImplementedError):
    def __init__(self, *args: object) -> None:
        super().__init__("Unknown resource type", *args)


@attrs.define(auto_exc=True)
class ContentTooLarge(OSError):
    received: int
    max_size: int


@attrs.define(auto_exc=True)
class ResponseNotOk(OSError):
    status: int


async def read_response_content(
    response: aiohttp.ClientResponse, max_size: int | None = None, chunk_size: int = -1
) -> Result[io.BytesIO, aiohttp.ClientError | ContentTooLarge]:
    if max_size is None:
        try:
            content = await response.content.read()

        except aiohttp.ClientError as exc:
            return Err(exc)

        return Ok(io.BytesIO(content))

    if response.content_length is not None and response.content_length > max_size:
        return Err(ContentTooLarge(response.content_length, max_size))

    bio = io.BytesIO()

    async for chunk in (
        response.content.iter_chunked(chunk_size)
        if chunk_size != -1
        else response.content.iter_any()
    ):
        bio.write(chunk)

        if bio.tell() > max_size:
            return Err(ContentTooLarge(bio.tell(), max_size))

    bio.seek(0)
    return Ok(bio)


async def read_file(resource: FileResource, /) -> io.BytesIO:
    _LOG.info("Open path=%s", resource.path)
    return io.BytesIO(await anyio.Path(resource.path).read_bytes())


async def read_http(
    resource: HttpResource, /, max_size: int | None = None, chunk_size: int = -1
) -> Result[io.BytesIO, aiohttp.ClientError | ContentTooLarge | ResponseNotOk]:
    async with http.session.get(resource.url) as response:
        if response.status != http.ResponseStatus.ok:
            return Err(ResponseNotOk(response.status))

        return await read_response_content(response, max_size, chunk_size)


async def read_resource(
    resource: Resource, /, max_size: int | None = None, chunk_size: int = -1
) -> Result[io.BytesIO, aiohttp.ClientError | ContentTooLarge | ResponseNotOk]:
    match resource:
        case FileResource() as file:
            result = Ok(await read_file(file))

        case HttpResource() as web_resource:
            result = await read_http(web_resource, max_size, chunk_size)

        case _:
            msg = "Unknown resource type"
            raise NotImplementedError(msg)

    return result
