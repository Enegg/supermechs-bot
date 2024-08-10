import typing
from collections import abc
from typing import Any, ClassVar, Generic

import anyio
import attrs

from discord import InteractionLimits

from app.typeshed import AsyncFunc, P, RetT, T
from memo import AsyncMemo, default_key


def async_memoize(func: AsyncFunc[P, T], /) -> AsyncFunc[P, T]:
    """Memoization decorator for async functions.

    It is safe to run the resulting coroutine function concurrently to self using same
    arguments, in which case the decorated awaitable is ran only once.
    """
    key = typing.cast(abc.Callable[P, abc.Hashable], default_key)
    return AsyncMemo(func, key)


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


@attrs.define
class Deferred(Generic[T]):
    """Future-like object."""

    _sentinel: ClassVar[Any] = object()

    _value: T = attrs.field(default=_sentinel, init=False)
    _event: anyio.Event = attrs.field(factory=anyio.Event, init=False)

    def set(self, value: T, /) -> None:
        """Set the value and awaken waiters."""
        self._value = value
        self._event.set()

    def is_set(self) -> bool:
        """Whether the value has been set."""
        return self._event.is_set()

    async def get(self) -> T:
        """Wait for value to be set and return it."""
        await self._event.wait()
        return self._value

    def get_nowait(self) -> T:
        """Get the underlying value without awaiting."""
        if self._value is self._sentinel:
            msg = "Value access before .set"
            raise LookupError(msg)

        return self._value
