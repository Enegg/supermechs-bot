import os
import traceback
from collections import abc
from pathlib import PurePath
from typing import Literal, TypeAlias, get_args as get_type_args

from disnake.utils import utcnow as utcnow

__all__ = ("as_binary_unit", "atoi_bin", "format_exception", "utcnow")


# https://en.wikipedia.org/wiki/Binary_prefix
BinaryPrefix: TypeAlias = Literal["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi"]
BINARY_PREFIXES: abc.Sequence[BinaryPrefix] = get_type_args(BinaryPrefix)


def as_binary_unit(b: int, /, prefix: BinaryPrefix = "") -> tuple[int, BinaryPrefix]:
    """Return a tuple representing the value in a binary prefixed unit.

    >>> fold_binary_unit(256 * 1024)
    (256, "Ki")

    The optional `prefix` offsets the returned prefix by associated exponent.

    >>> fold_binary_unit(256 * 1024, "Gi")
    (256, "Ti")
    """
    if b < 0:
        msg = "Cannot fold negative value"
        raise ValueError(msg)

    # 0.bit_length() - 1 < 0
    if b == 0:
        return 0, BINARY_PREFIXES[0]

    try:
        initial_exponent = BINARY_PREFIXES.index(prefix)
    except ValueError:
        msg = f"Unknown binary prefix: {prefix!r}"
        raise ValueError(msg) from None

    exponent = min(
        (b.bit_length() - 1) // 10,
        len(BINARY_PREFIXES) - 1 - initial_exponent,
    )
    b >>= 10 * exponent
    return b, BINARY_PREFIXES[initial_exponent + exponent]


def atoi_bin(value: str, /) -> int:
    """Parse a string to int, with respect to its binary prefix (Ki/Mi/…).

    >>> atoi_bin("10MiB")
    10485760
    """
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
    # TODO: make it work with ExceptionGroups too
    tb = traceback.TracebackException.from_exception(exc, compact=True)
    cwd = PurePath(os.getcwd())  # noqa: PTH109

    for frame_summary in tb.stack:
        file = PurePath(frame_summary.filename)

        try:
            relative_path = file.relative_to(cwd)

        except ValueError:
            continue

        frame_summary.filename = f".{os.sep}{relative_path}"

    return "".join(tb.format())
