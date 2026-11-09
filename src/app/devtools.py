import rich

from disnake.ui.action_row import normalize_components_to_dict

from app import ui
from app.core import state

__all__ = ("debug_components",)


def debug_components(components: ui.MessageComponents, /) -> None:
    if not state.debug_log_components:
        return

    component_payload, _ = normalize_components_to_dict(components)
    rich.print(component_payload)
