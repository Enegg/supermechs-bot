from __future__ import annotations

import typing as t
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from aiohttp import ClientSession


__all__ = ("IO_CLIENT",)


IO_CLIENT: ContextVar["ClientSession"] = ContextVar("session")
"""The aiohttp.ClientSession available for general use."""
