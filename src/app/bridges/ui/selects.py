from collections import abc

from discord.limits import ComponentLimits
from disnake import SelectOption, ui
from disnake.utils import MISSING

__all__ = ("PaginatedSelect",)


class PaginatedSelect(ui.StringSelect[None]):
    """Select menu which paginates options into chunks.

    Uses two `SelectOption`s to move between chunks.
    """

    option_up: SelectOption
    option_down: SelectOption
    page: int

    def __init__(
        self,
        *,
        up: SelectOption,
        down: SelectOption,
        custom_id: str = MISSING,
        all_options: abc.Iterable[SelectOption] = (),
        placeholder: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(custom_id=custom_id, placeholder=placeholder, disabled=disabled)
        self._all_options = list(all_options) or []
        self.option_up = up
        self.option_down = down
        self.page = 0
        self._update_page()

    @property
    def total_pages(self) -> int:
        """The total number of pages this select has."""
        total_option_count = len(self._all_options)

        if total_option_count <= ComponentLimits.select_options:
            return 1

        first_and_last_page = (ComponentLimits.select_options - 1) * 2

        if total_option_count <= first_and_last_page:
            # fits on two pages so we only add one of up/down option on each
            return 2

        non_extreme_pages, last_page_option_count = divmod(
            total_option_count - first_and_last_page,
            ComponentLimits.select_options - 2,
        )
        return 2 + non_extreme_pages + (last_page_option_count > 0)

    @property
    def all_options(self) -> abc.Sequence[SelectOption]:
        """All underlying `SelectOption`s."""
        return self._all_options

    @all_options.setter
    def all_options(self, new: abc.Iterable[SelectOption], /) -> None:
        self._all_options = list(new)
        self.page = 0
        self._update_page()

    def update_on_own_option(self, option_id: str, /) -> bool:
        if option_id == self.option_up.value:
            self.page -= 1

        elif option_id == self.option_down.value:
            self.page += 1

        else:
            return False

        self._update_page()
        return True

    def _update_page(self) -> None:
        page = self.page
        total = self.total_pages

        options = self._underlying.options
        options.clear()

        if total <= 1:
            # fits in the option limit, do not add the up/down options
            options[:] = self._all_options

        elif page == 0:
            options[:] = self._all_options[: ComponentLimits.select_options - 1]
            options.append(self.option_down)

        elif page == total - 1:
            # the +1 accounts for first page containing one extra option
            offset = (ComponentLimits.select_options - 2) * page + 1
            options.append(self.option_up)
            options += self._all_options[offset:]

        else:
            offset = (ComponentLimits.select_options - 2) * page + 1
            size = ComponentLimits.select_options - 2
            options.append(self.option_up)
            options += self._all_options[offset : offset + size]
            options.append(self.option_down)
