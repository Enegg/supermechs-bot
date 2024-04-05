from __future__ import annotations

import typing as t
from typing_extensions import LiteralString

__all__ = ("fold_binary_prefix", "ReprMixin")

# https://en.wikipedia.org/wiki/Binary_prefix
BinaryPrefix: typing.TypeAlias = typing.Literal["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi"]
BINARY_PREFIXES: abc.Sequence[BinaryPrefix] = typing.get_args(BinaryPrefix)


def fold_binary_prefix(bytes_: int, /, prefix: BinaryPrefix = "") -> tuple[int, BinaryPrefix]:
    """Folds the number of bytes in increments of 1024, until it drops below 1024.

    Given `n = int(log(value, 1024))`, returns `(value // 1024 ** n, BINARY_PREFIXES[n])`.
    The optional `prefix` will offset the returned prefix by associated exponent.
    """
    if bytes_ < 0:
        msg = "Number of bytes cannot be negative"
        raise ValueError(msg)

    if bytes_ == 0:
        # necessary as .bit_length() - 1 would be negative
        return 0, BINARY_PREFIXES[0]

    try:
        current_exp = BINARY_PREFIXES.index(prefix)
    except ValueError:
        msg = f"Unknown binary prefix: {prefix!r}"
        raise ValueError(msg) from None

    exp = min(
        (bytes_.bit_length() - 1) // 10,
        len(BINARY_PREFIXES) - 1 - current_exp,
    )
    # equivalent to bytes_ //= 1024 ** exp
    bytes_ >>= 10 * exp
    return bytes_, BINARY_PREFIXES[current_exp + exp]


class ReprMixin:
    """Class for programmatic __repr__ creation."""

    __repr_attributes__: t.Iterable[str]
    __slots__ = ()

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_attributes__)
        return f"<{type(self).__name__} {attrs} at 0x{id(self):016X}>"
