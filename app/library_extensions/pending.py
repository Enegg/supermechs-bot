"""
Things that have pending PRs and/or will eventually be found in future library releases.
"""

import importlib
import pkgutil
import typing as t
from enum import Enum

if t.TYPE_CHECKING:
    from disnake.app_commands import APIApplicationCommand

__all__ = ("walk_modules", "command_mention", "InteractionEvent")


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


class InteractionEvent(str, Enum):
    """Enumeration of interaction related events."""

    interaction = "interaction"
    """Called when an interaction happened.
    This currently happens due to application command invocations or components being used.
    """
    message_interaction = "message_interaction"
    """Called when a message interaction happened. 
    This currently happens due to components being used.
    """
    modal_submit = "modal_submit"
    """Called when a modal is submitted."""
    button_click = "button_click"
    """Called when a button is clicked."""
    dropdown = "dropdown"
    """Called when a select menu is clicked."""


def command_mention(command: "APIApplicationCommand") -> str:
    """Returns a string allowing to mention a slash command."""
    return f"</{command.name}:{command.id}>"
