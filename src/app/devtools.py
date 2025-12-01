import rich

from disnake.ui.action_row import normalize_components_to_dict

from app import ui

__all__ = ("debug_components",)


debug_enabled: bool = False


def debug_components(components: ui.MessageComponents, /) -> None:
    if not debug_enabled:
        return

    component_payload, _ = normalize_components_to_dict(components)
    rich.print(component_payload)
