import os
import traceback
import typing
from collections import abc
from typing import Final, Literal, TypeAlias

__all__ = ("INVISIBLE_CHAR", "fold_binary_prefix", "unfold_binary_prefix", "format_exception")

INVISIBLE_CHAR: Final = "\u2800"
"""Invisible character discord does not truncate."""

# https://en.wikipedia.org/wiki/Binary_prefix
BinaryPrefix: TypeAlias = Literal["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi"]
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


def unfold_binary_prefix(value: str, /) -> int:
    i = len(value)

    for n, char in enumerate(value):
        if not char.isdecimal():
            i = n
            break

    if unit := value[i : i + 2]:
        value = value[:i]
        try:
            exp = BINARY_PREFIXES.index(unit, 1)

        except ValueError:
            msg = f"Unknown prefix: {unit!r}"
            raise ValueError(msg) from None

    else:
        exp = 0

    return int(value) << (10 * exp)


def format_exception(exc: BaseException, /) -> str:
    """Format the exception's traceback into a string.

    Makes paths embedded within the message relative to the cwd.
    """
    return "".join(traceback.format_exception(exc)).replace(os.getcwd(), ".")  # noqa: PTH109
