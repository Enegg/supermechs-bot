import asyncio
import os
import typing
import typing_extensions as typing_
from collections import abc

from disnake import Client, Event, MessageInteraction, ModalInteraction
from disnake.ui import Modal

__all__ = ("HasCustomID", "metadata_of", "random_str", "wait_for_components", "wait_for_modal")


def random_str() -> str:
    """Generates a random string."""
    return os.urandom(16).hex()


class HasCustomID(typing.Protocol):
    @property
    def custom_id(self) -> str:
        ...


def metadata_of(component: HasCustomID, /, sep: str = ":") -> abc.Sequence[str]:
    return component.custom_id.split(sep, 1)[1:]


IDHolderT = typing_.TypeVar("IDHolderT", bound=HasCustomID | str, infer_variance=True)


async def wait_for_components(
    *components_or_ids: IDHolderT,
    client: Client,
    user_id: int | None = None,
    timeout: float = 600,
) -> tuple[MessageInteraction, IDHolderT]:
    """Waits for an interaction with any of given components.

    If `user_id` is provided, ignores interactions from anyone but the specified user.
    """
    ids_to_components = {
        comp if isinstance(comp, str) else comp.custom_id: comp for comp in components_or_ids
    }

    if user_id is None:

        def check(inter: MessageInteraction, /) -> bool:
            return inter.data.custom_id in ids_to_components

    else:

        def check(inter: MessageInteraction, /) -> bool:
            return inter.author.id == user_id and inter.data.custom_id in ids_to_components

    try:
        component_inter: MessageInteraction = await client.wait_for(
            Event.message_interaction, check=check, timeout=timeout
        )

    except asyncio.TimeoutError:
        raise TimeoutError from None

    return (component_inter, ids_to_components[component_inter.data.custom_id])


async def wait_for_modal(
    modal_or_id: Modal | str, client: Client, *, user_id: int | None = None, timeout: float = 600
) -> ModalInteraction:
    """Waits for a modal submission.

    If `user_id` is provided, ignores interactions from anyone but the specified user.
    """
    if not isinstance(modal_or_id, str):
        modal_or_id = modal_or_id.custom_id

    if user_id is None:

        def check(inter: ModalInteraction, /) -> bool:
            return inter.data.custom_id == modal_or_id

    else:

        def check(inter: ModalInteraction, /) -> bool:
            return inter.author.id == user_id and inter.data.custom_id == modal_or_id

    try:
        return await client.wait_for(Event.modal_submit, check=check, timeout=timeout)

    except asyncio.TimeoutError:
        raise TimeoutError from None
