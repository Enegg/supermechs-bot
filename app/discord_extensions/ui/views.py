from __future__ import annotations

import asyncio
import os
import typing as t
import typing_extensions as tex
from functools import partial

from disnake import MessageInteraction
from disnake.ui import ActionRow, MessageUIComponent, View
from disnake.ui.item import DecoratedItem, Item

from shared.utils import ReprMixin

from ..limits import ComponentLimits, MessageLimits
from .action_row import ActionRowT, PaginatedRow

if t.TYPE_CHECKING:
    from typeshed import Factory

__all__ = (
    "View",
    "SaneView",
    "PaginatorView",
    "invoker_bound",
    "positioned",
    "add_callback",
)

ItemT = tex.TypeVar("ItemT", bound=Item[None], default=Item[None], infer_variance=True)
ItemCallbackType = t.Callable[[t.Any, ItemT, MessageInteraction], t.Coroutine[t.Any, t.Any, None]]


class ViewP(t.Protocol):
    @property
    def user_id(self) -> int:
        ...

    async def interaction_check(self, interaction: MessageInteraction, /) -> bool:
        ...


ViewT = t.TypeVar("ViewT", bound=ViewP)


def invoker_bound(view: type[ViewT], /) -> type[ViewT]:
    """Mark a view invoker-bound.

    Components of such views can only be interacted with by the invoker.
    """
    response = "Only the command invoker can interact with that."

    async def interaction_check(self: ViewT, interaction: MessageInteraction, /) -> bool:
        if interaction.author.id == self.user_id:
            return True

        await interaction.send(response, ephemeral=True)
        return False

    view.interaction_check = interaction_check
    return view


def positioned(row: int, column: int):
    """Denotes the position of an Item in the 5x5 grid."""

    def decorator(func: ItemCallbackType[ItemT] | DecoratedItem[ItemT]) -> DecoratedItem[ItemT]:
        func.__discord_ui_position__ = (row, column)  # type: ignore
        return func  # type: ignore

    return decorator


class SaneView(t.Generic[ActionRowT], ReprMixin, View):
    """Represents a UI view.

    Parameters
    ----------
    timeout:
        Timeout in seconds from last interaction with the UI before no longer accepting input.
        If ``None`` then there is no timeout.
    """

    __repr_attributes__ = ("timeout", "rows")
    rows: tuple[ActionRowT, ActionRowT, ActionRowT, ActionRowT, ActionRowT]

    __view_children_items__: t.ClassVar[list[ItemCallbackType[MessageUIComponent]]] = []

    def __init_subclass__(cls, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        children: list[ItemCallbackType[MessageUIComponent]] = [
            member
            for base in reversed(cls.__mro__)
            for member in base.__dict__.values()
            if hasattr(member, "__discord_ui_model_type__")
        ]

        if len(children) > MessageLimits.action_rows * ComponentLimits.row_width:
            raise TypeError("View cannot have more than 25 children")

        cls.__view_children_items__ = children

    def __init__(
        self,
        *,
        timeout: float = 180.0,
        row_factory: Factory[ActionRowT] = ActionRow[MessageUIComponent],
    ) -> None:
        # we *do not* call super().__init__() and instead do all the initialization
        # so as to overwrite how View initializes decorated callbacks
        self.timeout = timeout

        self.rows = (row_factory(), row_factory(), row_factory(), row_factory(), row_factory())

        for item_or_func in self.__view_children_items__:
            column: int | None = None

            item: MessageUIComponent = item_or_func.__discord_ui_model_type__(
                **item_or_func.__discord_ui_model_kwargs__
            )
            item.callback = partial(item_or_func, self, item)
            setattr(self, item_or_func.__name__, item)
            # futureproofing in case I decide to remove rows from items
            row: int | None = getattr(item, "row", None)

            if hasattr(item_or_func, "__discord_ui_position__"):
                row, column = item_or_func.__discord_ui_position__

            item._view = self

            if row is None:
                raise TypeError(
                    "This view does not support auto rows,"
                    f" set row for item {item.custom_id} via @positioned"
                )

            action_row = self.rows[row]
            action_row.insert_item(len(action_row) if column is None else column, item)

        self.id: str = os.urandom(16).hex()
        self._View__cancel_callback: t.Callable[[tex.Self], None] | None = None
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

        if not 0 <= row < MessageLimits.action_rows:
            raise ValueError("row outside range 0-4")

        self.rows[row].append_item(item)

        item._view = self

    def remove_item(self, item: MessageUIComponent, row: int | None = None) -> None:
        if row is not None:
            self.rows[row].remove_item(item)
            return

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
    item: ItemT, callback: t.Callable[[ItemT, MessageInteraction], t.Coroutine[t.Any, t.Any, t.Any]]
) -> ItemT:
    item.callback = partial(callback, item)
    return item