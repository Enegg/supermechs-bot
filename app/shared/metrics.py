from __future__ import annotations

import asyncio
from pathlib import Path

import psutil

_sloc: int | None = None


def _get_sloc(directory: str) -> int:
    sloc = 0

    for path in Path(directory).glob("**/*.py"):
        with path.open(encoding="utf8") as file:
            for line in file:
                if not line or line.startswith("#"):
                    continue

                sloc += 1

    return sloc


async def get_sloc(directory: str = ".") -> int:
    """Get the source lines of code of python files within the directory."""
    global _sloc

    if _sloc is not None:
        return _sloc

    _sloc = await asyncio.to_thread(_get_sloc, directory)
    return _sloc


def get_ram_utilization(pid: int | None = None, /) -> int:
    """Returns the current process RAM utilization, in bytes."""
    return psutil.Process(pid).memory_info().rss
