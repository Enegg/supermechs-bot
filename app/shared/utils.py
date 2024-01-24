from __future__ import annotations

import typing as t
from typing_extensions import LiteralString

__all__ = ("wrap_bytes", "ReprMixin")


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
