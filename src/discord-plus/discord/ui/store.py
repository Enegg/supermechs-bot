from collections import abc
from typing import Final, TypeAlias
from typing_extensions import TypeVar

import anyio
import anyio.lowlevel
import attrs

import disnake
from discord.typeshed import T
from disnake import MessageInteraction

from .helpers import HasCustomID, random_str

__all__ = ("ComponentStore",)

ItemT = TypeVar("ItemT", bound=HasCustomID, infer_variance=True)
InteractionCallback: TypeAlias = abc.Callable[[MessageInteraction], abc.Awaitable[T]]
DecoRetType: TypeAlias = abc.Callable[[InteractionCallback[None]], ItemT]


async def default_check(inter: MessageInteraction, /) -> bool:
    await anyio.lowlevel.checkpoint()
    return True


@attrs.define
class ComponentStore:
    id: Final[str] = attrs.field(factory=random_str)
    """Unique ID of this store."""
    interaction_check: InteractionCallback[bool] = attrs.field(default=default_check)
    """A callback to determine whether an interaction should be propagated to the components."""

    _callbacks: dict[str, InteractionCallback[None]] = attrs.field(factory=dict, init=False)
    """Mapping of component's `custom_id`s to their callbacks."""
    _cancel_scope: anyio.CancelScope = attrs.field(factory=anyio.CancelScope, init=False)
    """CancelScope used to stop the main loop by timeout or .stop call."""
    _id_counter: int = attrs.field(default=0, init=False)
    """Counter used to generate IDs for components."""

    async def listen(self, client: disnake.Client, timeout: float = 600) -> bool:
        """Run the main loop until cancelled.

        Return `True` on timeout and `False` if stopped by `.stop`.
        """
        def check(inter: MessageInteraction) -> bool:
            return inter.data.custom_id in self._callbacks

        while True:
            self._cancel_scope.deadline = anyio.current_time() + timeout

            with self._cancel_scope as cs:
                inter: MessageInteraction = await client.wait_for(
                    disnake.Event.message_interaction, check=check
                )

            if cs.cancelled_caught:
                return cs.deadline <= anyio.current_time()

            if not await self.interaction_check(inter):
                continue

            await self._callbacks[inter.data.custom_id](inter)

    def stop(self) -> None:
        """Stop the loop and signal to `.listen` method to return."""
        self._cancel_scope.cancel()

    def bind(self, component: ItemT, /) -> DecoRetType[ItemT]:
        """Register a callback as a part of the store."""

        def catch_callback(func: InteractionCallback[None]) -> ItemT:
            self._callbacks[component.custom_id] = func
            return component

        return catch_callback

    def make_id(self, *parts: str) -> str:
        """Create a custom ID with a header, binding it to the store."""
        if not parts:
            id = f"{self.id}:{self._id_counter}"
            self._id_counter += 1
            return id

        return ":".join((self.id, *parts))

    def strip_id(self, component: HasCustomID, /) -> str:
        """Remove the header from a component's custom ID."""
        return component.custom_id.removeprefix(self.id + ":")
