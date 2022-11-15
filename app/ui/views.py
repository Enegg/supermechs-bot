from __future__ import annotations

import asyncio
import os
import typing as t
from functools import partial

from disnake import MessageInteraction
from disnake.ui.action_row import MessageUIComponent
from disnake.ui.item import DecoratedItem, Item
from disnake.ui.view import View
from typing_extensions import Self, TypeVar

from library_extensions import ReprMixin
from typeshed import T

from .action_row import ActionRow, ActionRowT, PaginatedRow

__all__ = ("View", "InteractionCheck", "PaginatorView", "V", "positioned")

V = TypeVar("V", bound=View | None, default=None, infer_variance=True)
I = TypeVar("I", bound=Item[None], infer_variance=True)
M = TypeVar("M", bound=MessageInteraction, default=MessageInteraction, infer_variance=True)
# how do I exit this
ItemCallbackType = t.Callable[[V, I, M], t.Coroutine[t.Any, t.Any, t.Any]]
FactoryT = type[T] | t.Callable[[], T]


class InteractionCheck:
    """Mixin to add an interaction_check which locks interactions to user_id.
    Note: remember to place this class before the view class, otherwise the view
    will overwrite the method."""

    user_id: int
    response = "Only the command invoker can interact with that."

    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        if interaction.author.id != self.user_id:
            await interaction.send(self.response, ephemeral=True)
            return False

        return True


def positioned(row: int, column: int):
    """Denotes the position of an Item in the 5x5 grid."""

    def decorator(func: ItemCallbackType[t.Any, I] | DecoratedItem[I]) -> DecoratedItem[I]:
        func.__discord_ui_position__ = (row, column)  # type: ignore
        return func  # type: ignore

    return decorator


class SaneView(t.Generic[ActionRowT], ReprMixin, View):
    """Represents a UI view.

    This object must be inherited to create a UI within Discord.

    Parameters
    ----------
    timeout: Optional[:class:`float`]
        Timeout in seconds from last interaction with the UI before no longer accepting input.
        If ``None`` then there is no timeout.
    """

    __repr_attributes__ = ("timeout", "rows")
    rows: tuple[ActionRowT, ActionRowT, ActionRowT, ActionRowT, ActionRowT]

    __view_children_items__: t.ClassVar[
        list[MessageUIComponent | ItemCallbackType[Self, MessageUIComponent]]
    ] = []

    def __init_subclass__(cls, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        children: list[MessageUIComponent | ItemCallbackType[Self, MessageUIComponent]] = [
            member
            for base in reversed(cls.__mro__)
            for member in base.__dict__.values()
            if hasattr(member, "__discord_ui_model_type__")
        ]

        if len(children) > 25:
            raise TypeError("View cannot have more than 25 children")

        cls.__view_children_items__ = children

    def __init__(
        self,
        *,
        timeout: float = 180.0,
        row_factory: FactoryT[ActionRowT] = ActionRow[MessageUIComponent],
    ) -> None:
        # we *do not* call super().__init__() and instead do all the initialization
        # so as to overwrite how View initializes decorated callbacks
        self.timeout = timeout

        self.rows = (row_factory(), row_factory(), row_factory(), row_factory(), row_factory())

        for item_or_func in self.__view_children_items__:
            column: int | None = None

            if not isinstance(item_or_func, Item):
                item: MessageUIComponent = item_or_func.__discord_ui_model_type__(
                    **item_or_func.__discord_ui_model_kwargs__
                )
                item.callback = partial(item_or_func, self, item)
                setattr(self, item_or_func.__name__, item)
                row = getattr(item, "row", None)  # futureproofing in case I decide to remove rows
                # from items

                if hasattr(item_or_func, "__discord_ui_position__"):
                    row, column = item_or_func.__discord_ui_position__

            else:
                item = item_or_func
                row = getattr(item, "row", None)

            item._view = self

            if row is None:
                raise TypeError(
                    f"This view does not support auto rows, set row for item {item.custom_id} via @positioned"
                )

            action_row = self.rows[row]
            action_row.insert_item(len(action_row) if column is None else column, item)

        self.id: str = os.urandom(16).hex()
        self._View__cancel_callback: t.Callable[[Self], None] | None = None
        self._View__timeout_expiry: float | None = None
        self._View__timeout_task: asyncio.Task[None] | None = None
        self._View__stopped: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

    @t.overload
    def __getitem__(self, pos: int) -> ActionRowT:
        ...

    @t.overload
    def __getitem__(self, pos: tuple[int, int]) -> MessageUIComponent:
        ...

    def __getitem__(self, pos: int | tuple[int, int]) -> MessageUIComponent | ActionRowT:
        if isinstance(pos, int):
            return self.rows[pos]

        elif isinstance(pos, tuple):
            row, item = pos
            return self.rows[row][item]

        raise TypeError("Expected int or tuple of two ints")

    def __delitem__(self, pos: int | tuple[int, int]) -> None:
        if isinstance(pos, int):
            self.rows[pos].clear_items()

        elif isinstance(pos, tuple):
            row, item = pos
            del self.rows[row][item]

        raise TypeError("Expected int or tuple of two ints")

    @property
    def children(self):
        # for compatibility, not recommended to use
        return [item for row in self.rows for item in row.children]

    @t.overload
    def add_item(self, item: MessageUIComponent) -> None:
        ...

    @t.overload
    def add_item(self, item: MessageUIComponent, row: int) -> None:
        ...

    def add_item(self, item: MessageUIComponent, row: int | None = None) -> None:
        if not isinstance(item, Item):
            raise TypeError(f"expected Item, not {item.__class__!r}")

        if row is None and item.row is not None:
            row = item.row

        elif row is None:
            raise ValueError("Cannot add an item without row specified")

        if not 0 <= row < 5:
            raise ValueError("row outside range 0-4")

        self.rows[row].append_item(item)

        item._view = self

    def remove_item(self, item: MessageUIComponent, row: int | None = None) -> None:
        if row is not None:
            self.rows[row].remove_item(item)

        else:
            for _row in self.rows:
                try:
                    _row.remove_item(item)
                    return

                except ValueError:
                    pass

    def clear_items(self) -> None:
        """Removes all items from the view."""

        for row in self.rows:
            row.clear_items()

    def to_components(self):
        return [row.to_component_dict() for row in self.rows if len(row) != 0]


class PaginatorView(SaneView[PaginatedRow[MessageUIComponent]]):
    """View implementing simple button pagination."""

    __repr_attributes__ = ("timeout", "rows")

    def __init__(self, *, timeout: float = 180.0, columns: int = 5) -> None:
        super().__init__(
            timeout=timeout, row_factory=lambda: PaginatedRow[MessageUIComponent](columns=columns)
        )

    @property
    def columns(self) -> int:
        return self.rows[0].columns

    @property
    def page(self) -> int:
        return self.rows[0].page

    @page.setter
    def page(self, value: int) -> None:
        for row in self.rows:
            row.page = value


def add_callback(
    item: I, callback: t.Callable[[I, MessageInteraction], t.Coroutine[t.Any, t.Any, t.Any]]
) -> I:
    item.callback = partial(callback, item)
    return item
