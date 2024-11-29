import io
from typing import Any

import aiohttp
import anyio

from discord import InteractionLimits

from app.typeshed import AsyncFunc, RetT, T


async def amap(coro: AsyncFunc[[T], RetT], /, *args: T) -> list[RetT]:
    """Asynchronously map coroutine function over arguments."""
    sentinel: Any = object()
    values: list[RetT] = [sentinel] * len(args)

    async def worker(arg: T, index: int) -> None:
        values[index] = await coro(arg)

    async with anyio.create_task_group() as tg:
        for i, arg in enumerate(args):
            tg.start_soon(worker, arg, i)

    return values


def move_on_before_timeout(threshold: float = 0.5, /) -> anyio.CancelScope:
    """Create a cancel scope which timeouts before interaction response."""
    return anyio.move_on_after(InteractionLimits.response_timeout - threshold)


class ContentSizeError(OSError): ...


async def read_content(
    response: aiohttp.ClientResponse, max_size: int | None = None, chunk_size: int = -1
) -> io.BytesIO:
    if max_size is None:
        bio = io.BytesIO(await response.content.read())
        bio.seek(0)
        return bio

    if (response.content_length or 0) > max_size:
        raise ContentSizeError

    bio = io.BytesIO()

    async for chunk in (
        response.content.iter_chunked(chunk_size)
        if chunk_size != -1
        else response.content.iter_any()
    ):
        bio.write(chunk)

        if bio.tell() > max_size:
            raise ContentSizeError

    bio.seek(0)
    return bio
