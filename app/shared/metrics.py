import typing
from collections import Counter
from threading import Lock

import anyio
import anyio.to_thread
import psutil

from async_utils import async_memoize
from typeshed import Pathish


def _file_sloc(path: Pathish, /) -> int:
    sloc = 0

    with open(path, encoding="utf8") as file:  # noqa: PTH123
        for line in map(str.lstrip, file):
            if not line or line.startswith(("#", '"""')):
                continue

            sloc += 1

    return sloc


@async_memoize
async def get_sloc(directory: Pathish = ".", /) -> int:
    """Get the number of source lines of code of python files within the directory."""
    total: int = 0
    write_lock = Lock()

    def runner(path: Pathish, /) -> None:
        nonlocal total
        with write_lock:
            total += _file_sloc(path)

    async with anyio.create_task_group() as tg:
        async for path in anyio.Path(directory).glob("**/*.py"):
            tg.start_soon(anyio.to_thread.run_sync, runner, path)  # pyright: ignore[reportArgumentType]

    return total


def get_ram_utilization(pid: int | None = None, /) -> int:
    """Returns the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss


class CommandData(typing.NamedTuple):
    id: int
    name: str


command_invocations: typing.Final = Counter[CommandData]()


def add_invocation(id: int, name: str, /) -> None:
    command_invocations[CommandData(id, name)] += 1
