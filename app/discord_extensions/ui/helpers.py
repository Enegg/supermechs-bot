import asyncio
import os
import typing
from collections import abc

from disnake import Client, Event, MessageInteraction, ModalInteraction
from disnake.ui import Modal

__all__ = ("HasCustomID", "metadata_of", "random_str", "wait_for_component", "wait_for_modal")


def random_str() -> str:
    """Generates a random string."""
    return os.urandom(16).hex()


class HasCustomID(typing.Protocol):
    @property
    def custom_id(self) -> str:
        ...


def metadata_of(component: HasCustomID, /, sep: str = ":") -> abc.Sequence[str]:
    return component.custom_id.split(sep, 1)[1:]


async def wait_for_component(
    client: Client, component_or_id: HasCustomID | str, timeout: float = 600
) -> MessageInteraction:
    """Wrapper for simple single component UI listeners."""

    if not isinstance(component_or_id, str):
        component_or_id = component_or_id.custom_id

    def check(inter: MessageInteraction, /) -> bool:
        return inter.data.custom_id == component_or_id

    try:
        return await client.wait_for(Event.message_interaction, check=check, timeout=timeout)

    except asyncio.TimeoutError:
        raise TimeoutError from None


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
