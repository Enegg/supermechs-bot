from __future__ import annotations

import typing as t
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from aiohttp import ClientSession


SESSION_CTX: ContextVar["ClientSession"] = ContextVar("session")
"""The aiohttp.ClientSession instantiated by the bot."""
