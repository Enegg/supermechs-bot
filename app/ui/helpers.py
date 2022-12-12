import typing as t

from disnake import Client, MessageInteraction, ModalInteraction
from disnake.ui import Modal

from library_extensions import InteractionEvent

__all__ = ("wait_for_component", "wait_for_modal", "HasCustomID")


class HasCustomID(t.Protocol):
    @property
    def custom_id(self) -> str:
        ...


async def wait_for_component(
    client: Client, component_or_id: HasCustomID | str, timeout: float = 600
) -> MessageInteraction:
    """Wrapper for simple single component UI listeners."""

    if not isinstance(component_or_id, str):
        component_or_id = component_or_id.custom_id

    def check(inter: MessageInteraction) -> bool:
        return inter.data.custom_id == component_or_id

    return await client.wait_for(InteractionEvent.message_interaction, check=check, timeout=timeout)


async def wait_for_modal(
    client: Client, modal_or_id: Modal | str, timeout: float = 600
) -> ModalInteraction:
    """Wrapper for a simple modal listener."""

    if isinstance(modal_or_id, Modal):
        modal_or_id = modal_or_id.custom_id

    def check(inter: ModalInteraction) -> bool:
        return inter.data.custom_id == modal_or_id

    return await client.wait_for(InteractionEvent.modal_submit, check=check, timeout=timeout)
