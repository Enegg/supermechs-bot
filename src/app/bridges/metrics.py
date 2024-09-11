import typing
from collections import Counter
from threading import Lock

import anyio
import anyio.to_thread
import psutil

from app.async_utils import async_memoize
from app.typeshed import Pathish

__all__ = ("get_sloc", "get_ram_utilization", "add_invocation", "invoke_counter")


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


def get_ram_utilization(pid: int | None = None, /) -> int:
    """Return the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss


class CommandData(typing.NamedTuple):
    id: int
    name: str


invoke_counter: typing.Final = Counter[CommandData]()


def add_invocation(id: int, name: str, /) -> None:
    invoke_counter[CommandData(id, name)] += 1
