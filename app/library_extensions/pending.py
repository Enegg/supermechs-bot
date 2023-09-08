"""
Things that have pending PRs and/or will eventually be found in future library releases.
"""

import importlib
import pkgutil
import typing as t
from enum import Enum

__all__ = ("walk_modules", "command_mention", "OPTION_LIMIT", "MSG_CHAR_LIMIT", "MAX_RESPONSE_TIME")


def walk_modules(
    paths: t.Iterable[str],
    prefix: str = "",
    ignore: t.Iterable[str] | t.Callable[[str], bool] | None = None,
) -> t.Iterator[str]:
    if isinstance(ignore, t.Iterable):
        ignore_tup = tuple(ignore)
        ignore = lambda path: path.startswith(ignore_tup)  # noqa: E731

    seen: set[str] = set()

    for _, name, ispkg in pkgutil.iter_modules(paths, prefix):
        if ignore is not None and ignore(name):
            continue

        if not ispkg:
            yield name
            continue

        module = importlib.import_module(name)

        if hasattr(module, "setup"):
            yield name
            continue

        sub_paths: list[str] = []

        for path in module.__path__ or ():
            if path not in seen:
                seen.add(path)
                sub_paths.append(path)

        if sub_paths:
            yield from walk_modules(sub_paths, name + ".", ignore)


class Commandish(t.Protocol):
    @property
    def id(self) -> int:
        ...

    @property
    def name(self) -> str:
        ...


def command_mention(command: Commandish, /) -> str:
    """Returns a string allowing to mention a slash command."""
    return f"</{command.name}:{command.id}>"


OPTION_LIMIT = 25
"""Limit related to select and autocomplete options."""

MSG_CHAR_LIMIT = 2000
"""Message content character limit."""


class EmbedLimits(int, Enum):
    title = 256
    description = 4096
    field_name = 256
    field_value = 1024
    footer_text = 2048
    author_name = 256


MAX_RESPONSE_TIME = 3
"""Maximum amount of time in second bot can take to respond to an interaction."""
