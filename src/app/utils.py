import io
import os
import traceback
from collections import abc
from typing import Literal, Self, get_args as get_type_args, override

from disnake.utils import utcnow as utcnow

from app import paths
from app.typeshed import Pathish

__all__ = ("StringBuilder", "as_binary_unit", "atoi_bin", "format_exception", "utcnow")


# https://en.wikipedia.org/wiki/Binary_prefix
type BinaryPrefix = Literal["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi"]
BINARY_PREFIXES: abc.Sequence[BinaryPrefix] = get_type_args(BinaryPrefix.__value__)
assert BINARY_PREFIXES


def as_binary_unit(b: int, /, prefix: BinaryPrefix = "") -> tuple[int, BinaryPrefix]:
    """Return a tuple representing the value in a binary prefixed unit.

    >>> as_binary_unit(256 * 1024)
    (256, "Ki")

    The optional `prefix` offsets the returned prefix by associated exponent.

    >>> as_binary_unit(256 * 1024, "Gi")
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


def normalize_traceback(tb: traceback.TracebackException, /) -> None:
    """Normalize a `TracebackException`.

    This makes file paths relative to the cwd.
    """
    if hasattr(tb, "filename"):  # 'filename' is only present for SyntaxErrors
        tb.filename = strip_cwd(tb.filename)

    for frame_summary in tb.stack:
        if frame_summary.filename.startswith("<"):
            continue

        try:
            frame_summary.filename = strip_cwd(frame_summary.filename)

        except ValueError:
            continue

    if tb.exceptions:
        for child_tb in tb.exceptions:
            normalize_traceback(child_tb)


def format_exception(exc: BaseException, /) -> str:
    """Format an exception's traceback into a string."""
    tb = traceback.TracebackException.from_exception(exc, compact=True)
    normalize_traceback(tb)
    return "".join(tb.format())


def strip_cwd(path: Pathish, /) -> str:
    """Make path relative to the cwd. `{cwd}/pth` becomes `pth`.

    Raises
    ------
    ValueError
        Path is not within the cwd.
    """
    return os.path.relpath(path, paths.CWD)


class StringBuilder:
    """Wrapper around `io.StringIO`, providing convenience chaining methods."""

    __slots__ = ("sio",)

    sio: io.StringIO

    def __init__(self, initial: str = "", /) -> None:
        self.sio = io.StringIO(initial_value=initial)

    # NOTE: len() also provides bool()
    def __len__(self) -> int:
        return self.sio.tell()

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.build()!r})"

    def add(self, s: str, /) -> Self:
        """Write string `s` to the buffer."""
        self.sio.write(s)
        return self

    def add_many(self, *s: str) -> Self:
        """Write multiple strings to the buffer."""
        self.sio.writelines(s)
        return self

    def add_from(self, it: abc.Iterable[str], /) -> Self:
        """Write multiple strings to the buffer from iterable `it`."""
        self.sio.writelines(it)
        return self

    def add_repeated(self, s: str, count: int, /) -> Self:
        """Write string `s` * `count` times to the buffer."""
        # TODO: is a while loop faster, or s * count?
        while count > 0:
            self.sio.write(s)
            count -= 1
        return self

    def build(self) -> str:
        """Return the string contents of the buffer."""
        return self.sio.getvalue()
