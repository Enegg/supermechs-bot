import typing
import typing_extensions as typing_
from collections import abc

import anyio
import anyio.lowlevel
import attrs
import disnake
from disnake import MessageInteraction, ui

from typeshed import T

from .helpers import HasCustomID, random_str

__all__ = ("ComponentStore",)

ItemT = typing_.TypeVar("ItemT", bound=ui.Item[None], infer_variance=True)
InteractionCallback: typing.TypeAlias = abc.Callable[[MessageInteraction], abc.Awaitable[T]]
DecoRetType: typing.TypeAlias = abc.Callable[[InteractionCallback[None]], ItemT]


async def default_check(inter: MessageInteraction, /) -> bool:
    await anyio.lowlevel.checkpoint()
    return True


@attrs.define
class ComponentStore:
    id: typing.Final[str] = attrs.field(factory=random_str)
    """Unique ID of this store. It'll be prepended to custom IDs of all child components."""
    interaction_check: InteractionCallback[bool] = attrs.field(default=default_check)
    """A callback to determine whether an interaction should be propagated to the components."""

    _callbacks: dict[str, InteractionCallback[None]] = attrs.field(factory=dict, init=False)
    """Mapping of component's `custom_id`s to their callbacks."""
    _cancel_scope: anyio.CancelScope = attrs.field(factory=anyio.CancelScope, init=False)
    """CancelScope used to stop the main loop by timeout or .stop call."""

    async def listen(self, client: disnake.Client, timeout: float = 600) -> bool:
        """Run the main loop of the store, until it times out or `.stop` is called.
        Returns True in the former case, and False in the latter.
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
        """Stops the loop and causes the `.listen` method to return."""
        self._cancel_scope.cancel()

    def bind(self, component: ItemT, custom_id: str | None = None) -> DecoRetType[ItemT]:
        """Register a component as a part of the store.
        Will prepend the component's `custom_id` with own id.
        """
        if custom_id is None:
            custom_id = random_str()

        custom_id = f"{self.id}:{custom_id}"

        def catch_callback(func: InteractionCallback[None]) -> ItemT:
            self._callbacks[custom_id] = func
            component._underlying.custom_id = custom_id  # pyright: ignore[reportPrivateUsage]

            return component

        return catch_callback

    def strip_id(self, component: HasCustomID, /) -> str:
        """Remove the part added by the store from a component's custom ID."""
        return component.custom_id.removeprefix(self.id + ":")
