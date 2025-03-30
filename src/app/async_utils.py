from typing import Any, cast as type_cast, overload
from typing_extensions import TypeVar

import anyio

from discord import InteractionLimits

from app.typeshed import AsyncFunc, RetT, T


async def amap(coro: AsyncFunc[[T], RetT], /, *args: T) -> list[RetT]:
    """Asynchronously map coroutine function over arguments."""
    values: list[RetT] = [type_cast("Any", None)] * len(args)

    async def worker(arg: T, index: int) -> None:
        values[index] = await coro(arg)

    async with anyio.create_task_group() as tg:
        for i, arg in enumerate(args):
            tg.start_soon(worker, arg, i)

    return values


T1 = TypeVar("T1", infer_variance=True)
T2 = TypeVar("T2", infer_variance=True)
T3 = TypeVar("T3", infer_variance=True)
T4 = TypeVar("T4", infer_variance=True)


# fmt: off
@overload
async def gather(c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], /) -> tuple[T1, T2]: ...
@overload
async def gather(c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], /) -> tuple[T1, T2, T3]: ... # noqa: E501
@overload
async def gather(c1: AsyncFunc[[], T1], c2: AsyncFunc[[], T2], c3: AsyncFunc[[], T3], c4: AsyncFunc[[], T4], /) -> tuple[T1, T2, T3, T4]: ...  # noqa: E501
# fmt: on
@overload
async def gather(*coros: AsyncFunc[[], T]) -> tuple[T, ...]: ...
async def gather(*coros: AsyncFunc[[], T]) -> tuple[T, ...]:  # pyright: ignore[reportInconsistentOverload]
    out: list[T] = [type_cast("Any", None)] * len(coros)

    async def worker(index: int, coro: AsyncFunc[[], T]) -> None:
        out[index] = await coro()

    async with anyio.create_task_group() as tg:
        for i, coro in enumerate(coros):
            tg.start_soon(worker, i, coro)

    return tuple(out)


def move_on_before_timeout(threshold: float = 0.5, /) -> anyio.CancelScope:
    """Create a cancel scope which timeouts before interaction response."""
    return anyio.move_on_after(InteractionLimits.response_timeout - threshold)
