from __future__ import annotations

import typing as t
from collections import Counter

import anyio
import psutil

from .utils import async_memoize

if t.TYPE_CHECKING:
    import os


def _file_sloc(path: os.PathLike[str], /) -> int:
    sloc = 0

    with open(path, encoding="utf8") as file:  # noqa: PTH123
        for line in file:
            if not line or line.lstrip().startswith(("#", '"""')):
                continue

            sloc += 1

    return sloc


@async_memoize
async def get_sloc(directory: str = ".", /) -> int:
    """Get the number of source lines of code of python files within the directory."""
    results: list[int] = []

    def runner(path: os.PathLike[str], /) -> None:
        results.append(_file_sloc(path))

    async with anyio.create_task_group() as tg:
        async for path in anyio.Path(directory).glob("**/*.py"):
            tg.start_soon(anyio.to_thread.run_sync, runner, path)

    return sum(results)


def get_ram_utilization(pid: int | None = None, /) -> int:
    """Returns the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss


class CommandData(t.NamedTuple):
    id: int
    name: str


command_invocations: t.Final = Counter[CommandData]()


def add_invocation(id: int, name: str, /) -> None:
    command_invocations[CommandData(id, name)] += 1
