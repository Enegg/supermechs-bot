from collections import abc
from typing import ClassVar

from discord.limits import ComponentLimits
from disnake import SelectOption, ui
from disnake.utils import MISSING

__all__ = ("PaginatedSelect",)


class PaginatedSelect(ui.StringSelect[None]):
    """Select menu which paginates options into chunks.

    Uses two `SelectOption`s to move between chunks.
    """

    __repr_attributes__: ClassVar[tuple[str, ...]] = (  # pyright: ignore[reportIncompatibleVariableOverride]
        *ui.StringSelect.__repr_attributes__,
        "option_up",
        "option_down",
        "page",
        "all_options",
    )

    option_up: SelectOption
    option_down: SelectOption
    page: int
    _all_options: abc.Sequence[SelectOption]

    def __init__(
        self,
        *,
        option_up: SelectOption,
        option_down: SelectOption,
        page: int = 0,
        all_options: abc.Sequence[SelectOption] = (),
        custom_id: str = MISSING,
        placeholder: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(custom_id=custom_id, placeholder=placeholder, disabled=disabled)
        self._all_options = all_options
        self.option_up = option_up
        self.option_down = option_down
        self.page = page
        self._update_page()

    @property
    def total_pages(self) -> int:
        """The total number of pages this select has."""
        total_option_count = len(self._all_options)

        if total_option_count <= ComponentLimits.select_options:
            return 1

        first_and_last_page = (ComponentLimits.select_options - 1) * 2

        if total_option_count <= first_and_last_page:
            # fits on two pages, add one of up/down option on each
            return 2

        size = ComponentLimits.select_options - 2
        return 2 + (total_option_count - first_and_last_page + size - 1) // size

    @property
    def all_options(self) -> abc.Sequence[SelectOption]:
        """All underlying `SelectOption`s."""
        return self._all_options

    @all_options.setter
    def all_options(self, new: abc.Sequence[SelectOption], /) -> None:
        self._all_options = new
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
            options += self._all_options

        elif page == 0:
            options += self._all_options[: ComponentLimits.select_options - 1]
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
