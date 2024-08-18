from collections import abc
from typing import Final, Generic

from attrs import define, field

from discord.typeshed import T

__all__ = ("Paginator",)


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
