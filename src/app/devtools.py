from typing import Any, Protocol

import rich

import disnake
from disnake.ui.action_row import normalize_components_to_dict

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
        component_payload, _ = normalize_components_to_dict(components)
        parts.append(component_payload)

    rich.print(*parts)


class ComponentStructure(Protocol):
    def to_component_dict(self) -> dict[str, Any]: ...


def debug_components(components: ComponentStructure, /) -> None:
    if not debug_enabled:
        return

    rich.print(components.to_component_dict())
