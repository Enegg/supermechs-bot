import typing as t

from disnake import SelectOption
from disnake.ui.select import StringSelect
from disnake.utils import MISSING

from .. import ComponentLimits

__all__ = ("EMPTY_OPTION", "PaginatedSelect")

EMPTY_OPTION: t.Final = SelectOption(label="empty", description="Select to remove", emoji="🗑️")


class PaginatedSelect(StringSelect[None]):
    """Select which paginates options into chunks of 23-25 and registers two
    `SelectOption`s to move between chunks."""

    def __init__(
        self,
        *,
        up: SelectOption,
        down: SelectOption,
        custom_id: str = MISSING,
        all_options: t.Iterable[SelectOption] = (),
        placeholder: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(custom_id=custom_id, placeholder=placeholder, disabled=disabled)
        self._all_options = list(all_options) or []
        self.up = up
        self.down = down
        self._page = 0
        self._update_page()

    @property
    def page(self) -> int:
        """The current page number."""
        return self._page

    @page.setter
    def page(self, page: int, /) -> None:
        if not 0 <= page < self.total_pages:
            raise IndexError("Page out of bounds")
        self._page = page
        self._update_page()

    @property
    def total_pages(self) -> int:
        """The total number of pages this select has."""
        total_option_count = len(self._all_options)

        if total_option_count <= ComponentLimits.select_options:
            return 1

        if total_option_count <= (ComponentLimits.select_options - 1) * 2:
            # fits on two pages so we only add one of up/down option on each
            return 2

        both_options_pages, last_page_options = divmod(
            total_option_count - (ComponentLimits.select_options - 1) * 2,
            ComponentLimits.select_options - 2,
        )
        return 2 + both_options_pages + (1 if last_page_options > 0 else 0)

    @property
    def all_options(self) -> t.Sequence[SelectOption]:
        """All underlying `SelectOption`s."""
        return self._all_options

    @all_options.setter
    def all_options(self, new: t.Iterable[SelectOption], /) -> None:
        self._all_options = list(new)
        self._page = 0
        self._update_page()

    def is_own_option(self, option_id: str, /) -> t.Literal[-1, 0, 1]:
        return 1 if option_id == self.up.value else -1 if option_id == self.down.value else 0

    def _update_page(self) -> None:
        page = self.page
        total = self.total_pages

        if total <= 1:
            # fits in the option limit so we need not to add the switch page options
            options = self._all_options

        elif page == 0:
            options = self._all_options[: ComponentLimits.select_options - 1]
            options.append(self.down)

        elif page == total - 1:
            # the +1 accounts for first page containing one extra option
            offset = (ComponentLimits.select_options - 2) * page + 1
            options = [self.up]
            options += self._all_options[offset:]

        else:
            offset = (ComponentLimits.select_options - 2) * page + 1
            size = ComponentLimits.select_options - 2
            options = [self.up]
            options += self._all_options[offset : offset + size]
            options.append(self.down)

        self._underlying.options = options
