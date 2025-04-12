import os
from collections import abc
from typing import Any, Protocol, overload

type Factory[RetT] = abc.Callable[[], RetT]
"""0-argument callable returning an object of given type."""
type Pathish = os.PathLike[str] | str
"""Path-like or a string representing a path."""
type AsyncFunc[**P, RetT] = abc.Callable[P, abc.Awaitable[RetT]]
"""Function yielding an awaitable."""
type Coro[RetT] = abc.Coroutine[Any, Any, RetT]
"""Shorthand for coroutine."""
type CoroFunc[**P, RetT] = abc.Callable[P, Coro[RetT]]
"""Function yielding a coroutine."""

type JsonPrimitive = str | int | float | bool | None
type JsonArray[ValueT: Json = Json] = abc.Sequence[ValueT]
type JsonObject[ValueT: Json = Json] = abc.Mapping[str, ValueT]
type Json = JsonPrimitive | JsonArray | JsonObject
"""Strict JSON type."""


class Getter[T, U](Protocol):
    """Abstract property implementing `__get__`."""

    @overload
    def __get__(self, obj: None, cls: type | None, /) -> T: ...
    @overload
    def __get__(self, obj: object, cls: type | None, /) -> U: ...
