from __future__ import annotations

import typing as t
from typing_extensions import LiteralString

from typeshed import P, T

from .manager import AsyncManager, default_key

__all__ = ("wrap_bytes", "is_pascal", "ReprMixin")


def wrap_bytes(
    value: int, unit: LiteralString = "iB"
) -> tuple[int, LiteralString]:
    """Convert absolute byte size to suffixed unit."""
    if value == 0:
        return 0, unit

    prefixes = ("", "K", "M", "G", "T")
    exp = min((value.bit_length() - 1) // 10, len(prefixes) - 1)
    value >>= 10 * exp
    return value, prefixes[exp] + unit


class ReprMixin:
    """Class for programmatic __repr__ creation."""

    __repr_attributes__: t.Iterable[str]
    __slots__ = ()

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_attributes__)
        return f"<{type(self).__name__} {attrs} at 0x{id(self):016X}>"


def is_pascal(string: str) -> bool:
    """Returns True if the string is pascal-cased string, False otherwise.

    A string is pascal-cased if it is a single word that starts with a capitalized letter.
        >>> is_pascal("fooBar")
        False
        >>> is_pascal("FooBar")
        True
        >>> is_pascal("Foo Bar")
        False
    """
    return string[:1].isupper() and " " not in string


def async_memoize(func: t.Callable[P, t.Awaitable[T]], /) -> t.Callable[P, t.Awaitable[T]]:
    """Memoization decorator for async functions.

    It is safe to run the resulting coroutine function concurrently to self using same
    arguments, in which case the decorated coro is ran only once.
    """
    key = t.cast(t.Callable[P, t.Hashable], default_key)
    manager = AsyncManager(func, key)
    return manager.lookup_or_create
