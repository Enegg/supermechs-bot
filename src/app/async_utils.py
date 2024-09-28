from collections import abc
from typing import Any, ClassVar
from typing_extensions import override

import anyio
import attrs

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


@attrs.define
class Deferred(abc.Awaitable[T]):
    """Future-like object."""

    _sentinel: ClassVar[Any] = object()

    _value: T = attrs.field(default=_sentinel, init=False)
    _event: anyio.Event = attrs.field(factory=anyio.Event, init=False)

    @override
    def __await__(self) -> abc.Generator[Any, Any, T]:
        yield from self._event.wait().__await__()
        return self._value

    def set(self, value: T, /) -> None:
        """Set the value and awaken waiters."""
        self._value = value
        self._event.set()

    def is_set(self) -> bool:
        """Whether the value has been set."""
        return self._event.is_set()

    def get_nowait(self) -> T:
        """Get the underlying value without awaiting."""
        if self._value is self._sentinel:
            msg = "Value access before .set"
            raise LookupError(msg)

        return self._value
