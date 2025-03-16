from threading import Lock

import anyio
import anyio.to_thread
import psutil

from app.typeshed import Pathish

__all__ = ("get_ram_usage", "get_sloc")


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


def get_ram_usage(pid: int | None = None, /) -> int:
    """Return the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss
