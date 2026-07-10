import os
import pathlib
import reprlib
import traceback
from collections import ChainMap, abc
from threading import Lock
from typing import Any, Final, Literal, Self, get_args as get_type_args

import anyio
import anyio.to_thread
import attrs
import cattrs
import msgspec
import psutil
import rtoml
from monads.option import Null, Option, Some

from discord.emoji import AnyEmoji, CustomEmoji, UnicodeEmoji
from disnake import Color, PartialEmoji
from disnake.utils import utcnow as utcnow

from app import paths
from app.typeshed import ByteSize, Pathish
from resources import AnyResource, from_uri

__all__ = ("as_binary_unit", "atoi_bin", "format_exception", "limited_repr", "utcnow")

_repr_obj = reprlib.Repr()
_repr_obj.maxdict = 20
limited_repr = _repr_obj.repr
del _repr_obj

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


def format_exception(exc: BaseException, /) -> str:
    """Format the exception's traceback into a string.

    Makes paths embedded within the message relative to the cwd.
    """
    # TODO: make it work with ExceptionGroups too
    tb = traceback.TracebackException.from_exception(exc, compact=True)

    for frame_summary in tb.stack:
        try:
            frame_summary.filename = strip_cwd(frame_summary.filename)

        except ValueError:
            continue

    return "".join(tb.format())


def strip_cwd(path: Pathish, /) -> str:
    """Make path relative to the cwd. `{cwd}/pth` becomes `pth`.

    Raises
    ------
    ValueError
        Path is not within the cwd.
    """
    return os.path.relpath(path, paths.CWD)


def get_ram_usage(process: psutil.Process, /) -> int:
    """Return a process' RAM utilization, in bytes."""
    return process.memory_info().rss


def _file_sloc(path: Pathish, /) -> int:
    sloc = 0

    with open(path, encoding="utf-8") as file:  # noqa: PTH123
        for line in map(str.lstrip, file):
            if not line or line.startswith(("#", '"""')):
                continue

            sloc += 1

    return sloc


async def get_sloc(directory: Pathish = ".", /) -> int:
    """Get the number of significant lines of code of python files within the directory."""
    total: int = 0
    write_lock = Lock()

    def runner(path: Pathish, /) -> None:
        nonlocal total
        sloc = _file_sloc(path)
        with write_lock:
            total += sloc

    async with anyio.create_task_group() as tg:
        async for path in anyio.Path(directory).glob("**/*.py"):
            tg.start_soon(anyio.to_thread.run_sync, runner, path)

    return total


def chain_maps[KT, VT](*maps: abc.Mapping[KT, VT]) -> abc.Mapping[KT, VT]:
    # ChainMap expects MutableMappings, but we only care about its immutable API
    return ChainMap(*maps)  # pyright: ignore[reportArgumentType]


def unset_to_option[T](v: T | msgspec.UnsetType, /) -> Option[T]:
    """Return `Null.null` for `msgspec.UNSET`, `Some(T)` otherwise."""
    return Null.null if v is msgspec.UNSET else Some(v)


CONVERTER: Final = cattrs.Converter()


@CONVERTER.register_structure_hook
def _structure_color(value: int, cls: type) -> Color:
    return Color(int(value))


def _structure_resource(value: str, cls: type) -> AnyResource:
    assert isinstance(value, str)
    return from_uri(value)


CONVERTER.register_structure_hook_func(lambda x: x is AnyResource, _structure_resource)


def _structure_emoji(value: str, cls: type) -> AnyEmoji:
    partial_emoji = PartialEmoji.from_str(value)
    if partial_emoji.id is None:
        return UnicodeEmoji(partial_emoji.name)
    return CustomEmoji(partial_emoji.id, partial_emoji.name, partial_emoji.animated)


CONVERTER.register_structure_hook_func(lambda x: x is AnyEmoji, _structure_emoji)


@CONVERTER.register_structure_hook
def _structure_binary_int(value: Any, _: object) -> ByteSize:
    try:
        return ByteSize(int(value))

    except (ValueError, TypeError):
        pass

    if not isinstance(value, str):
        msg = f"Invalid type: {value!r}"
        raise TypeError(msg) from None

    return ByteSize(atoi_bin(value))


del _structure_color, _structure_resource, _structure_binary_int


@attrs.define
class MappingParser:
    mappings: list[abc.Mapping[str, Any]]
    conv: cattrs.Converter

    def __init__(
        self, *mappings: abc.Mapping[str, Any], conv: cattrs.Converter = CONVERTER
    ) -> None:
        self.mappings = list(mappings)
        self.conv = conv

    def structure[T](self, cls: type[T], *key_path: str) -> T:
        config: abc.Mapping[str, Any] = chain_maps(*self.mappings)

        for key in key_path:
            config = config[key]

        return self.conv.structure(config, cls)

    @classmethod
    def from_path(
        cls,
        path: Pathish,
        loader: abc.Callable[[str], abc.Mapping[str, Any]] = rtoml.loads,
    ) -> Self:
        path = pathlib.Path(path)
        config = loader(path.read_text(encoding="utf-8"))
        return cls(config)
