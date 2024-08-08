import os
from collections import abc
from typing import Final, Generic, Protocol
from typing_extensions import TypeVar

import anyio
from attrs import define, field

from discord.typeshed import T

from disnake import Client, Event, MessageInteraction, ModalInteraction, ui

__all__ = (
    "HasCustomID",
    "Paginator",
    "random_str",
    "wait_for_components",
    "wait_for_modal",
)


def random_str() -> str:
    """Generates a random string."""
    return os.urandom(8).hex()


class HasCustomID(Protocol):
    @property
    def custom_id(self) -> str: ...


IDHolderT = TypeVar("IDHolderT", bound=HasCustomID | str, infer_variance=True)


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

    with anyio.fail_after(timeout):
        inter: MessageInteraction = await client.wait_for(Event.message_interaction, check=check)

    return (inter, ids_to_components[inter.data.custom_id])


async def wait_for_modal(
    modal_or_id: ui.Modal | str, client: Client, *, user_id: int | None = None, timeout: float = 600
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

    with anyio.fail_after(timeout):
        return await client.wait_for(Event.modal_submit, check=check)


@define
class Paginator(Generic[T]):
    """State machine proxying a value at a specific index of a sequence."""

    pages: Final[abc.Sequence[T]] = field()
    index: int = field(default=0)

    @property
    def page(self) -> T:
        return self.pages[self.index]

    @property
    def at_first_page(self) -> bool:
        """Whether the page is the first page."""
        return self.index == 0

    @property
    def at_last_page(self) -> bool:
        """Whether the page is the last page."""
        return self.index == len(self.pages) - 1

    def next_page(self) -> None:
        """Advance the page index."""
        if self.at_last_page:
            raise IndexError

        self.index += 1

    def prev_page(self) -> None:
        """Reduce the page index."""
        if self.at_first_page:
            raise IndexError

        self.index -= 1

    def goto(self, page: int, /) -> None:
        """Go to an absolute page index."""
        if not 0 <= page <= len(self.pages) - 1:
            raise IndexError(page)

        self.index = page

    def jump_by(self, page: int, /) -> None:
        """Jump by n pages."""

        if not 0 <= self.index + page <= len(self.pages) - 1:
            raise IndexError(page)

        self.index += page
