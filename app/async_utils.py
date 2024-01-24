import typing as t
from contextlib import asynccontextmanager

import anyio

from config import RESPONSE_TIME_LIMIT
from shared.manager import AsyncManager, default_key
from typeshed import P, RetT, T

AwaitableCallback = t.Callable[[T], t.Awaitable[RetT]]


def async_memoize(func: t.Callable[P, t.Awaitable[T]], /) -> t.Callable[P, t.Awaitable[T]]:
    """Memoization decorator for async functions.

    It is safe to run the resulting coroutine function concurrently to self using same
    arguments, in which case the decorated coro is ran only once.
    """
    key = t.cast(t.Callable[P, t.Hashable], default_key)
    manager = AsyncManager(func, key)
    return manager.get_or_create


async def amap(coro: AwaitableCallback[T, RetT], /, *args: T) -> list[RetT]:
    """Asynchronously map coroutine function over arguments."""
    # XXX: make it into AsyncIterator?
    sentinel: t.Any = object()
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
