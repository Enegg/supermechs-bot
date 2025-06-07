from collections import abc
from contextlib import asynccontextmanager
from typing import Any, cast as type_cast, overload

import anyio
import attrs

from app.typeshed import AsyncFunc


async def amap[T, RetT](coro: AsyncFunc[[T], RetT], /, *args: T) -> list[RetT]:
    """Asynchronously map coroutine function over arguments."""
    out: list[RetT] = [type_cast("Any", None)] * len(args)

    async def worker(index: int, arg: T) -> None:
        out[index] = await coro(arg)

    async with anyio.create_task_group() as tg:
        for i, arg in enumerate(args):
            tg.start_soon(worker, i, arg)

    return out


# fmt: off
@overload
async def gather[T1, T2](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], /) -> tuple[T1, T2]: ...
@overload
async def gather[T1, T2, T3](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], /) -> tuple[T1, T2, T3]: ...
@overload
async def gather[T1, T2, T3, T4](c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], c4: AsyncFunc[[], T4], /) -> tuple[T1, T2, T3, T4]: ...
# fmt: on
@overload
async def gather[T](*coros: AsyncFunc[[], T]) -> tuple[T, ...]: ...
async def gather[T](*coros: AsyncFunc[[], T]) -> tuple[T, ...]:  # pyright: ignore[reportInconsistentOverload]
    out: list[T] = [type_cast("Any", None)] * len(coros)

    async def worker(index: int, coro: AsyncFunc[[], T]) -> None:
        out[index] = await coro()

    async with anyio.create_task_group() as tg:
        for i, coro in enumerate(coros):
            tg.start_soon(worker, i, coro)

    return tuple(out)


@attrs.define
class LockManager[KT]:
    """Manager controlling `anyio.Lock` creation.

    The first context to acquire a lock under a given key will evict it on release.
    Subsequent access via the same key in that timeframe acquires the same lock.
    """

    _locks: dict[KT, anyio.Lock] = attrs.field(factory=dict, init=False)

    @asynccontextmanager
    async def acquire_for(self, key: KT, /) -> abc.AsyncIterator[None]:
        try:
            lock = self._locks[key]
            owner = False

        except KeyError:
            lock = self._locks[key] = anyio.Lock()
            owner = True

        try:
            async with lock:
                yield

        finally:
            if owner:
                del self._locks[key]
