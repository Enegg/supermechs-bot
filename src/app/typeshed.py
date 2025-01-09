import os
from collections import abc
from typing import Any, ParamSpec, Protocol, TypeAlias, overload
from typing_extensions import TypeVar

T = TypeVar("T", infer_variance=True)
U = TypeVar("U", infer_variance=True)
RetT = TypeVar("RetT", infer_variance=True)
"""Function return type variable."""
KT = TypeVar("KT", bound=abc.Hashable, infer_variance=True)
"""Key-type of a mapping."""
VT = TypeVar("VT", infer_variance=True)
"""Value-type of a mapping."""
P = ParamSpec("P")
"""Parameter specification of a callable."""

Factory: TypeAlias = abc.Callable[[], RetT]
"""0-argument callable returning an object of given type."""
Pathish: TypeAlias = os.PathLike[str] | str
"""Path-like or a string representing a path."""
AsyncFunc: TypeAlias = abc.Callable[P, abc.Awaitable[RetT]]
"""Function yielding an awaitable."""
Coro: TypeAlias = abc.Coroutine[Any, Any, RetT]
"""Shorthand for coroutine."""
CoroFunc: TypeAlias = abc.Callable[P, Coro[RetT]]
"""Function yielding a coroutine."""

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonArray: TypeAlias = abc.Sequence["Json"]
JsonObject: TypeAlias = abc.Mapping[str, "Json"]
Json: TypeAlias = JsonPrimitive | JsonArray | JsonObject
"""Strict JSON type."""


class Getter(Protocol[T, U]):
    """Abstract property implementing `__get__`."""

    @overload
    def __get__(self, obj: None, cls: type | None, /) -> T: ...

    @overload
    def __get__(self, obj: object, cls: type | None, /) -> U: ...
