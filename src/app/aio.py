import logging
import pathlib
from http import HTTPMethod as HTTPMethod, HTTPStatus as HTTPStatus
from typing import Any, Self, cast as type_cast, overload

import aiohttp
import anyio
import anyio.to_thread
import attrs
import orjson
import yarl
from aiohttp import ClientSession as HTTPSession

import disnake.http

from app.typeshed import AsyncFunc, Pathish, ResultTuple
from app.utils import as_binary_unit, async_result
from resources import AnyResource, FileResource, HttpResource

_LOG = logging.getLogger("io")

type HttpReadError = aiohttp.ClientError | ResponseNotOk


def client_session(client: disnake.http.HTTPClient, /) -> HTTPSession:
    """Create a HTTP session with client's connector & proxy."""

    # https://github.com/aio-libs/aiohttp/blob/64313cfc5024a316d85f34e7e77c9995a683e35f/aiohttp/payload.py#L441
    # aiohttp wants dumps(Any) -> str, then encodes it
    @attrs.define
    class _MockStr:
        proxied_bytes: bytes

        def encode(self, encoding: str = "", errors: str = "") -> bytes:
            return self.proxied_bytes

    def _dumps(obj: object, /) -> Any:
        return _MockStr(orjson.dumps(obj))

    return HTTPSession(
        connector=client.connector,
        connector_owner=client.connector is None,
        timeout=aiohttp.ClientTimeout(total=30),
        json_serialize=_dumps,
    )


async def read_path(path: Pathish, /) -> ResultTuple[bytes, OSError]:
    path = pathlib.Path(path)
    _LOG.info("Open path=%s", path)

    try:
        return await anyio.to_thread.run_sync(path.read_bytes), None

    except OSError as exc:
        return None, exc


@attrs.define(auto_exc=True)
class ResponseNotOk(OSError):
    status: HTTPStatus

    @classmethod
    def from_response(cls, response: aiohttp.ClientResponse, /) -> Self:
        return cls(HTTPStatus(response.status))


async def read_http(url: yarl.URL, /, session: HTTPSession) -> ResultTuple[bytes, HttpReadError]:
    _LOG.info("Request method=%s url=%s", HTTPMethod.GET, url)

    async with session.get(url) as response:
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

        if response.status != HTTPStatus.OK:
            return None, ResponseNotOk.from_response(response)

        return await async_result(response.content.read(), aiohttp.ClientError)


async def read_resource(
    resource: AnyResource, /, session: HTTPSession
) -> ResultTuple[bytes, HttpReadError | OSError]:
    match resource:
        case FileResource():
            return await read_path(resource.path)

        case HttpResource():
            return await read_http(resource.url, session)


# fmt: off
@overload
async def gather[T1, T2](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], /) -> tuple[T1, T2]: ...
@overload
async def gather[T1, T2, T3](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], /) -> tuple[T1, T2, T3]: ...
@overload
async def gather[T1, T2, T3, T4](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], c4: AsyncFunc[[], T4], /) -> tuple[T1, T2, T3, T4]: ...
@overload
async def gather[T1, T2, T3, T4, Tn](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], c4: AsyncFunc[[], T4], /, *cs: AsyncFunc[[], Tn]) -> tuple[T1, T2, T3, T4, *tuple[Tn, ...]]: ...
# fmt: on
async def gather[T](*coros: AsyncFunc[[], T]) -> tuple[T, ...]:  # pyright: ignore[reportInconsistentOverload]
    out: list[T] = [type_cast("T", None)] * len(coros)

    async def worker(index: int, coro: AsyncFunc[[], T]) -> None:
        out[index] = await coro()

    async with anyio.create_task_group() as tg:
        for i, coro in enumerate(coros):
            tg.start_soon(worker, i, coro)

    return tuple(out)


async def amap[T, RetT](coro: AsyncFunc[[T], RetT], /, *args: T) -> list[RetT]:
    """Asynchronously map coroutine function over arguments."""
    out: list[RetT] = [type_cast("RetT", None)] * len(args)

    async def worker(index: int, arg: T) -> None:
        out[index] = await coro(arg)

    async with anyio.create_task_group() as tg:
        for i, arg in enumerate(args):
            tg.start_soon(worker, i, arg)

    return out
