from __future__ import annotations

import typing as t

from typing_extensions import LiteralString

__all__ = ("wrap_bytes", "is_pascal", "ReprMixin")


def wrap_bytes(
    value: int, unit: LiteralString = "iB"
) -> tuple[int, LiteralString]:
    """Convert absolute byte size to suffixed unit."""
    if value == 0:
        return 0, unit

    exp = (value.bit_length() - 1) // 10
    value >>= 10 * exp
    prefixes = ("", "K", "M", "G", "T", "?")
    exp = min(exp, len(prefixes) - 1)
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
