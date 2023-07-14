from __future__ import annotations

import typing as t
from collections import Counter
from pathlib import Path

import anyio
import psutil

from typeshed import Coro, P, T

from .manager import AsyncManager, default_key


def async_memoize(func: t.Callable[P, Coro[T]], /) -> t.Callable[P, Coro[T]]:
    """Memoization decorator for async functions.

    It is safe to run the resulting coroutine function concurrently to self using same
    arguments, in which case the decorated coro is ran only once.
    """
    key = t.cast(t.Callable[P, t.Hashable], default_key)
    manager = AsyncManager(func, key)
    return manager.lookup_or_create



# async def _file_reader(path: anyio.Path, limiter: anyio.CapacityLimiter) -> int:
#     sloc = 0

#     async with limiter, await path.open(encoding="utf8") as file:
#         async for line in file:
#             if not line or line.lstrip().startswith("#"):
#                 continue

#             sloc += 1

#     return sloc


# async def _get_sloc_a(directory: str) -> int:
#     sloc = 0

#     limiter = anyio.CapacityLimiter(10)

#     async with anyio.create_task_group() as group:
#         async for path in anyio.Path(directory).glob("**/*.py"):
#             group.start_soon(_file_reader, path, limiter)



def _get_sloc(directory: str) -> int:
    sloc = 0

    for path in Path(directory).glob("**/*.py"):
        with path.open(encoding="utf8") as file:
            for line in file:
                if not line or line.lstrip().startswith("#"):
                    continue

                sloc += 1

    return sloc


@async_memoize
async def get_sloc(directory: str = ".") -> int:
    """Get the number of source lines of code of python files within the directory."""
    return await anyio.to_thread.run_sync(_get_sloc, directory)


def get_ram_utilization(pid: int | None = None, /) -> int:
    """Returns the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss


class CommandData(t.NamedTuple):
    id: int
    name: str


command_invocations = Counter[CommandData]()


def add_invocation(id: int, name: str, /) -> None:
    command_invocations[CommandData(id, name)] += 1
