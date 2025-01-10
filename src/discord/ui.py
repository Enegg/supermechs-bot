import os
from typing import Protocol
from typing_extensions import TypeVar

from discord.typeshed import ClientT
from disnake import Client, Event, MessageInteraction, ModalInteraction, ui


class HasCustomID(Protocol):
    @property
    def custom_id(self) -> str: ...


IDHolderT = TypeVar("IDHolderT", bound=HasCustomID | str, infer_variance=True)


def random_str() -> str:
    return os.urandom(16).hex()


async def wait_for_components(
    *components_or_ids: IDHolderT, client: ClientT, user_id: int | None = None
) -> tuple[MessageInteraction[ClientT], IDHolderT]:
    """Wait for an interaction with any of given components.

    If `user_id` is provided, ignore interactions from anyone but the specified user.
    """
    ids_to_components = {
        comp if isinstance(comp, str) else comp.custom_id: comp for comp in components_or_ids
    }

    if user_id is None:

        def check(inter: MessageInteraction[Client], /) -> bool:
            return inter.data.custom_id in ids_to_components

    else:

        def check(inter: MessageInteraction[Client], /) -> bool:
            return inter.author.id == user_id and inter.data.custom_id in ids_to_components

    inter: MessageInteraction[ClientT] = await client.wait_for(
        Event.message_interaction, check=check
    )
    return (inter, ids_to_components[inter.data.custom_id])


async def wait_for_modal(
    modal_or_id: ui.Modal | str, client: ClientT, *, user_id: int | None = None
) -> ModalInteraction[ClientT]:
    """Wait for a modal submission.

    If `user_id` is provided, ignore interactions from anyone but the specified user.
    """
    # XXX: does filtering by user make sense in modal context?
    if not isinstance(modal_or_id, str):
        modal_or_id = modal_or_id.custom_id

    if user_id is None:

        def check(inter: ModalInteraction[Client], /) -> bool:
            return inter.data.custom_id == modal_or_id

    else:

        def check(inter: ModalInteraction[Client], /) -> bool:
            return inter.author.id == user_id and inter.data.custom_id == modal_or_id

    return await client.wait_for(Event.modal_submit, check=check)
