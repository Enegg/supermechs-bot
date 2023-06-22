from __future__ import annotations

import asyncio
import typing as t
from functools import wraps
from pathlib import Path

import psutil

from typeshed import KT, VT, Coro


def cache_async_safe(func: t.Callable[[KT], Coro[VT]], /) -> t.Callable[[KT], Coro[VT]]:
    """Cache decorator for async functions which prevents concurrent calls to func using same arguments."""

    results = dict[KT, VT | asyncio.Future[VT]]()

    @wraps(func)
    async def wrapper(key: KT, /) -> VT:
        value_or_future = results.get(key)

        if value_or_future is not None:
            if isinstance(value_or_future, asyncio.Future):
                return await value_or_future

            return value_or_future

        fut = results[key] = asyncio.Future[VT]()
        result = await func(key)
        fut.set_result(result)
        results[key] = result
        return result

    return wrapper


def _get_sloc(directory: str) -> int:
    sloc = 0

    for path in Path(directory).glob("**/*.py"):
        with path.open(encoding="utf8") as file:
            for line in file:
                if not line or line.lstrip().startswith("#"):
                    continue

                sloc += 1

    return sloc


@cache_async_safe
async def get_sloc(directory: str = ".") -> int:
    """Get the source lines of code of python files within the directory."""
    return await asyncio.to_thread(_get_sloc, directory)


def get_ram_utilization(pid: int | None = None, /) -> int:
    """Returns the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss
