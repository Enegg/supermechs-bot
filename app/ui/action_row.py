from __future__ import annotations

import typing as t

from disnake.ui.action_row import ActionRow, StrictUIComponentT, UIComponentT
from disnake.ui.item import WrappedComponent

if t.TYPE_CHECKING:
    from .views import MessageUI

ActionRowT = t.TypeVar("ActionRowT", bound=ActionRow, covariant=True)

__all__ = ("ActionRowT", "ActionRow", "PaginatedRow")


class PaginatedRow(ActionRow[UIComponentT]):
    """Action row which divides added items into pages."""

    __repr_attributes__ = ("columns", "page", "persistent", "page_items")

    @t.overload
    def __init__(self: "PaginatedRow[WrappedComponent]", *, columns: int = 5) -> None:
        ...

    @t.overload
    def __init__(
        self: "PaginatedRow[WrappedComponent]", *components: None, columns: int = 5
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: "PaginatedRow[MessageUI[t.Any]]",
        *components: MessageUI[t.Any] | None,
        columns: int = 5,
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: "PaginatedRow[StrictUIComponentT]",
        *components: "StrictUIComponentT" | None,
        columns: int = 5,
    ) -> None:
        ...

    def __init__(self, *components: UIComponentT | None, columns: int = 5) -> None:
        if not 1 <= columns <= 5:
            raise ValueError("Columns must be between 1 and 5")

        size = sum(1 if item is None else item.width for item in components)

        if not 0 <= size <= 5:
            raise ValueError("Too many components to add.")

        super().__init__()
        self.page_items: list[UIComponentT] = []
        self.persistent: list[UIComponentT | None] = list(components)

        for _ in range(size, 5):  # size == 5 => nothing appended
            self.persistent.append(None)

        self.columns = columns
        self._page = 0

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_attributes__)
        return f"<{type(self).__name__} {attrs}>"

    def __setitem__(self, index: int, item: UIComponentT | None) -> None:
        if not isinstance(item, (WrappedComponent, type(None))):
            raise TypeError("Item must be a Select, Button or None.")

        self.persistent[index] = item

    @property
    def persistent_width(self) -> int:
        """The total width of only the elements that persist between pages."""
        return sum(item.width for item in self.persistent if item is not None)

    @property
    def current_page_items(self) -> list[UIComponentT]:
        """Non-persistent items that appear at current page."""
        columns = self.columns - self.persistent_width
        offset = self.page * columns
        return self.page_items[offset : offset + columns]

    @property
    def width(self) -> int:
        """The total width of all items that are on the current page."""
        return self.persistent_width + sum(item.width for item in self.current_page_items)

    def __len__(self) -> int:
        # this differs from width in that each item adds exactly 1 to len, despite its width.
        # also, since we don't care about items width, we can avoid slicing by doing *math*.
        length = persistent_width = 0

        for item in filter(None, self.persistent):
            length += 1
            persistent_width += item.width

        columns = self.columns - persistent_width  # we take the width

        return length + max(0, len(self.page_items) - self.page * columns)

    @property
    def page(self) -> int:
        return self._page

    @page.setter
    def page(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError(f"Expected an int, got {type(value)}")

        if value < 0:
            raise ValueError("Page cannot go below zero")

        self._page = value
        self.update()

    def insert_item(self, index: int, item: UIComponentT) -> None:
        present_width = 0 if (present := self.persistent[index]) is None else present.width

        if self.width + item.width - present_width > 5:
            raise ValueError("Too many components in this row, can not append a new one.")

        self.persistent[index] = item

    @t.overload
    def extend_page_items(self, component: UIComponentT, /, *components: UIComponentT) -> None:
        ...

    @t.overload
    def extend_page_items(self, component: t.Iterable[UIComponentT], /) -> None:
        ...

    def extend_page_items(
        self, component: UIComponentT | t.Iterable[UIComponentT], /, *components: UIComponentT
    ) -> None:
        """Appends passed components to the underlying page creator."""
        if isinstance(component, t.Iterable):
            self.page_items += component

        else:
            self.page_items.append(component)

        self.page_items += components

    def clear_items(self) -> None:
        self.clear_page()
        self.page_items.clear()
        self.persistent = [None] * 5

    def clear_page(self) -> None:
        """Removes items from current page."""
        self._children.clear()

    def update(self) -> None:
        """Updates the row with items that should be at given page."""
        self.clear_page()

        for item in self.current_page_items:
            self._children.append(item)

        for i, item in enumerate(self.persistent):
            if item is None:
                continue

            self._children.insert(i, item)
