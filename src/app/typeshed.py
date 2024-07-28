import os
import typing
import typing_extensions as typing_
from collections import abc

T = typing_.TypeVar("T", infer_variance=True)
T2 = typing_.TypeVar("T2", infer_variance=True)
RetT = typing_.TypeVar("RetT", infer_variance=True)
"""Function return type variable."""
KT = typing.TypeVar("KT", bound=abc.Hashable)
"""Key-type of a mapping."""
VT = typing.TypeVar("VT")
"""Value-type of a mapping."""
P = typing.ParamSpec("P")
"""Parameter specification of a callable."""

Factory: typing.TypeAlias = abc.Callable[[], RetT]
"""0-argument callable returning an object of given type."""
LiteralURL: typing.TypeAlias = str
"""String representing a URL."""
Pathish: typing.TypeAlias = os.PathLike[str] | str
"""Path-like or a string representing a path."""
AsyncFunc: typing.TypeAlias = abc.Callable[P, abc.Awaitable[RetT]]
"""Function yielding an awaitable."""
Coro: typing.TypeAlias = abc.Coroutine[typing.Any, typing.Any, RetT]
"""Shorthand for coroutine."""
CoroFunc: typing.TypeAlias = abc.Callable[P, Coro[RetT]]
"""Function yielding a coroutine."""


class Getter(typing.Protocol[T, T2]):
    """Abstract property implementing `__get__`."""

    @typing.overload
    def __get__(self, obj: None, cls: type | None, /) -> T:
        ...

    @typing.overload
    def __get__(self, obj: object, cls: type | None, /) -> T2:
        ...
