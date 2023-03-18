import typing as t

from disnake import SelectOption
from disnake.ui.select import Select, select
from disnake.utils import MISSING

S_CO = t.TypeVar("S_CO", bound=Select[None], covariant=True)


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
        self.page = 0  # calls property to set options

    def __len__(self) -> int:
        base = len(self._all_options)

        if base <= 25:
            # fits in the option limit so we need not to add the switch page options
            return 1

        elif base <= 48:
            # fits on two pages so we only add one switch option on each
            return 2

        full, part = divmod(base - 48, 23)
        # full is the number of pages that have both next & prev page buttons,
        # part is the number of options that will go to the last page
        return 2 + full + (part > 0)

    @property
    def page(self) -> int:
        """Current page of options"""
        return self._page

    @page.setter
    def page(self, page: int) -> None:
        self._page = int(page)

        if len(self) == 1:
            self._underlying.options = self._all_options

        elif page == 0:
            self._underlying.options = self._all_options[:24] + [self.down]

        elif page == len(self) - 1:
            self._underlying.options = [self.up] + self._all_options[page * 23 + 1 :]

        else:
            self._underlying.options = [
                x
                for y in (
                    (self.up,),
                    self._all_options[page * 23 + 1 : page * 23 + 24],
                    (self.down,),
                )
                for x in y
            ]

    @property
    def all_options(self) -> list[SelectOption]:
        """All underlying `SelectOption`s"""
        return self._all_options

    @all_options.setter
    def all_options(self, new: list[SelectOption]) -> None:
        self._all_options = new
        self.page = 0

    def check_option(self, option_id: str) -> bool:
        if option_id == self.up.value:
            self.page -= 1
            return True

        elif option_id == self.down.value:
            self.page += 1
            return True

        return False
