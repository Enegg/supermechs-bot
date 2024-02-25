import os
import typing
from collections import abc
from typing_extensions import ParamSpec, TypeVar

T = TypeVar("T", infer_variance=True)
T2 = TypeVar("T2", infer_variance=True)
RetT = TypeVar("RetT", infer_variance=True)
KT = TypeVar("KT", bound=abc.Hashable)
"""Key-type of a mapping."""
VT = TypeVar("VT")
"""Value-type of a mapping."""
P = ParamSpec("P")
"""Parameter specification of a callable."""

twotuple = tuple[T, T]
"""Tuple of two elements of same type."""
XOrTupleXY = T | tuple[T, T2]
"""Type or tuple of two types."""
Factory = abc.Callable[[], T]
"""0-argument callable returning an object of given type."""
LiteralURL: typing.TypeAlias = str
"""String representing a URL."""
Pathish: typing.TypeAlias = os.PathLike[str] | str
Coro: typing.TypeAlias = abc.Coroutine[typing.Any, typing.Any, T]
CoroFunc: typing.TypeAlias = abc.Callable[..., Coro[T]]


class Getter(typing.Protocol[T, T2]):
    """Abstract property implementing `__get__`."""

    @typing.overload
    def __get__(self, obj: None, cls: type | None, /) -> T:
        ...

    @typing.overload
    def __get__(self, obj: object, cls: type | None, /) -> T2:
        ...
