import rich

from discord import MessageBuilder
from disnake.ui.action_row import normalize_components_to_dict

__all__ = ("debug_components",)


debug_enabled: bool = False


def debug_components(builder: MessageBuilder, /) -> None:
    if not debug_enabled:
        return

    component_payload, _ = normalize_components_to_dict(builder.components)
    rich.print(component_payload)
