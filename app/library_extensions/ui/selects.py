import typing as t

from disnake import SelectOption
from disnake.ui.select import Select, select
from disnake.utils import MISSING

S_CO = t.TypeVar("S_CO", bound=Select[None], covariant=True)

OPTION_LIMIT = 25
EMPTY_OPTION: t.Final = SelectOption(label="empty", description="Select to remove", emoji="🗑️")

__all__ = ("select", "Select", "PaginatedSelect", "S_CO", "EMPTY_OPTION")


class PaginatedSelect(Select[None]):
    """Select which paginates options into chunks of 23-25 and registers two
    `SelectOption`s to move between chunks."""

    def __init__(
        self,
        *,
        up: SelectOption,
        down: SelectOption,
        custom_id: str,
        all_options: list[SelectOption] = MISSING,
        placeholder: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(custom_id=custom_id, placeholder=placeholder, disabled=disabled)
        self._all_options = all_options or []
        self.up = up
        self.down = down
        self._page = 0
        self._update_page()

    @property
    def page(self) -> int:
        """The current page number."""
        return self._page

    @property
    def total_pages(self) -> int:
        """The total number of <= 25 option pages this select has."""
        base = len(self._all_options)

        if base <= OPTION_LIMIT:
            # fits in the option limit so we need not to add the switch page options
            return 1

        if base <= (OPTION_LIMIT - 1) * 2:
            # fits on two pages so we only add one switch option on each
            return 2

        full, last = divmod(base - (OPTION_LIMIT - 1) * 2, OPTION_LIMIT - 2)
        # full is the number of pages that have both next & prev page buttons;
        # non-zero last means there's a last page with fewer than 24 options
        return 2 + full + int(last > 0)

    @property
    def all_options(self) -> list[SelectOption]:
        """All underlying `SelectOption`s."""
        return self._all_options

    @all_options.setter
    def all_options(self, new: list[SelectOption]) -> None:
        self._all_options = new
        self._page = 0
        self._update_page()

    def page_up(self) -> None:
        self._page -= 1
        self._update_page()

    def page_down(self) -> None:
        self._page += 1
        self._update_page()

    def _update_page(self) -> None:
        page = self.page
        total = self.total_pages

        if total <= 1:
            options = self._all_options

        elif page == 0:
            options = self._all_options[:OPTION_LIMIT - 1]
            options.append(self.down)

        elif page == total - 1:
            # the +1 accounts for first page containing one extra option
            offset = (OPTION_LIMIT - 2) * page + 1
            options = [self.up]
            options += self._all_options[offset:]

        else:
            offset = (OPTION_LIMIT - 2) * page + 1
            size = OPTION_LIMIT - 2
            options = [self.up]
            options += self._all_options[offset:offset + size]
            options.append(self.down)

        self._underlying.options = options

    def update_page_if_own_option(self, option_id: str, /) -> bool:
        """Update the page if the passed option's ID belongs to up/down option of the select."""
        if option_id == self.up.value:
            self.page_up()
            return True

        elif option_id == self.down.value:
            self.page_down()
            return True

        return False
