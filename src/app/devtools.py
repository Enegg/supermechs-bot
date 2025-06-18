import rich

import disnake
from disnake.ui.action_row import components_to_dict

from app import ui

__all__ = ("debug_message",)


debug_enabled: bool = False


def debug_message(
    embed: disnake.Embed | None = None, components: ui.MessageComponents = ()
) -> None:
    """Output the structure of a message to logs."""
    if not debug_enabled:
        return

    parts: list[object] = []

    if embed is not None:
        parts.append(f"Total size: {len(embed)}")
        parts.append(embed.to_dict())

    if components:
        parts.append(components_to_dict(components))

    rich.print(*parts)


def debug_components(components: ui.Container, /) -> None:
    if not debug_enabled:
        return

    rich.print(components.to_component_dict())
