import enum
import os
import pathlib
import reprlib
import threading
import traceback
from collections import ChainMap, abc
from typing import Literal, NamedTuple, get_args as get_type_args

import anyio
import anyio.to_thread
import msgspec
import rtoml

from disnake.utils import utcnow as utcnow

from app import paths
from app.typeshed import Pathish, ResultTuple

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


class SourceStats(NamedTuple):
    file_count: int = 0
    total_chars: int = 0
    total_lines: int = 0
    significant_lines: int = 0
    classes: int = 0
    functions: int = 0


async def get_source_stats(directory: Pathish = ".", /) -> SourceStats:
    """Get statistics about python source files within a directory."""
    total_lines = total_chars = significant_lines = classes = functions = 0
    write_lock = threading.Lock()

    def runner(path: Pathish, /) -> None:
        nonlocal total_lines, total_chars, significant_lines, classes, functions
        file_lines = file_chars = file_sig_lines = file_classes = file_functions = 0

        with open(path, encoding="utf-8") as file:  # noqa: PTH123
            for line in file:
                file_chars += len(line)
                file_lines += 1

                stripped_line = line.lstrip()
                if not stripped_line:
                    continue
                if not stripped_line.startswith(("#", '"""')):
                    file_sig_lines += 1
                if stripped_line.startswith("class "):
                    file_classes += 1
                if stripped_line.startswith(("def ", "async def ")):
                    file_functions += 1

        with write_lock:
            total_lines += file_lines
            total_chars += file_chars
            significant_lines += file_sig_lines
            classes += file_classes
            functions += file_functions

    file_count = 0

    async with anyio.create_task_group() as tg:
        async for path in anyio.Path(directory).glob("**/*.py"):
            tg.start_soon(anyio.to_thread.run_sync, runner, path)
            file_count += 1

    return SourceStats(file_count, total_chars, total_lines, significant_lines, classes, functions)


def chain_maps[KT, VT](maps: abc.Sequence[abc.Mapping[KT, VT]], /) -> abc.Mapping[KT, VT]:
    if len(maps) == 0:
        return {}
    if len(maps) == 1:
        return maps[0]
    # ChainMap expects MutableMappings, but we only care about its immutable API
    return ChainMap(*maps)  # pyright: ignore[reportArgumentType]


def unset_to_default[T](v: T | msgspec.UnsetType, /, default: T = None) -> T:
    """Return `default` for `msgspec.UNSET`, `v` otherwise."""
    return default if v is msgspec.UNSET else v


def try_enum[E: enum.Enum](key: str, enum_type: type[E]) -> E | None:
    try:
        return enum_type[key]
    except KeyError:
        return None


async def async_result[T, E: BaseException](
    coro: abc.Awaitable[T], /, *excs: type[E]
) -> ResultTuple[T, E]:
    try:
        return await coro, None

    except excs as err:
        return None, err


def read_and_parse_file[T](
    path: Pathish, /, *, type: type[T]
) -> ResultTuple[T, OSError | rtoml.TomlParsingError | msgspec.DecodeError]:
    path = pathlib.Path(path)

    match path.suffix:
        case ".toml":
            try:
                toml_text = path.read_text(encoding="utf-8")
            except OSError as exc:
                return None, exc

            try:
                toml_dict = rtoml.loads(toml_text)
            except rtoml.TomlParsingError as exc:
                return None, exc

            try:
                obj = msgspec.convert(toml_dict, type=type)
            except msgspec.DecodeError as exc:
                return None, exc

            return obj, None

        case ".json":
            try:
                json_bytes = path.read_bytes()
            except OSError as exc:
                return None, exc

            try:
                obj = msgspec.json.decode(json_bytes, type=type)
            except msgspec.DecodeError as exc:
                return None, exc

            return obj, None

        case unknown:
            return None, OSError(f"Unknown file type: {unknown!r}")
