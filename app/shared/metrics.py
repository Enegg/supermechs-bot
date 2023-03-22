from __future__ import annotations

from glob import iglob

import psutil

from .utils import wrap_bytes

_sloc: int | None = None


def get_sloc(directory: str = ".") -> int:
    """Get the source lines of code of python files within the directory."""
    global _sloc

    if _sloc is not None:
        return _sloc

    sloc = 0

    for path in iglob("**/*.py", root_dir=directory, recursive=True):
        with open(path, encoding="utf8") as file:
            for line in file:
                if not line or line.startswith("#"):
                    continue

                sloc += 1

    _sloc = sloc
    return sloc


def get_ram_utilization() -> tuple[int, str]:
    """Returns the current process RAM utilization as a tuple of (bits, exponent)"""
    process = psutil.Process()
    return wrap_bytes(process.memory_info().rss)
