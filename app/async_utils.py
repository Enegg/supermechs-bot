import typing
from collections import abc
from contextlib import asynccontextmanager

import anyio

from config import RESPONSE_TIME_LIMIT
from shared.manager import AsyncManager, default_key
from typeshed import AsyncFunc, P, RetT, T


def async_memoize(func: AsyncFunc[P, T], /) -> AsyncFunc[P, T]:
    """Memoization decorator for async functions.

    It is safe to run the resulting coroutine function concurrently to self using same
    arguments, in which case the decorated coro is ran only once.
    """
    key = typing.cast(abc.Callable[P, abc.Hashable], default_key)
    manager = AsyncManager(func, key)
    return manager.get_or_create


async def amap(coro: AsyncFunc[[T], RetT], /, *args: T) -> list[RetT]:
    """Asynchronously map coroutine function over arguments."""
    sentinel: typing.Any = object()
    values: list[RetT] = [sentinel] * len(args)

    async def worker(arg: T, index: int) -> None:
        values[index] = await coro(arg)

    async with anyio.create_task_group() as tg:
        for i, arg in enumerate(args):
            tg.start_soon(worker, arg, i)

    return values


@asynccontextmanager
async def move_on_before_timeout() -> t.AsyncIterator[None]:
    """Convenience context manager for stopping async block before interaction timeout."""

    async with anyio.move_on_after(RESPONSE_TIME_LIMIT):
        yield
