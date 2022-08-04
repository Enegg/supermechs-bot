import typing as t

from disnake import SelectOption
from disnake.ui.select import Select, select
from disnake.utils import MISSING

S_CO = t.TypeVar("S_CO", bound=Select, covariant=True)


EMPTY_OPTION: t.Final = SelectOption(label="empty", description="Select to remove", emoji="🗑️")

__all__ = ("select", "Select", "PaginatedSelect", "S_CO", "EMPTY_OPTION")


class PaginatedSelect(Select):
    """Select which paginates options into chunks of 23-25 and registers two
    `SelectOption`s to move between chunks."""

    def __init__(
        self,
        *,
        up: SelectOption,
        down: SelectOption,
        custom_id: str,
        options: list[SelectOption] = MISSING,
        placeholder: str | None = None,
        disabled: bool = False,
        row: int | None = None,
    ) -> None:
        super().__init__(custom_id=custom_id, placeholder=placeholder, disabled=disabled, row=row)
        self.all_options = options or []
        self.up = up
        self.down = down
        self.page = 0  # calls property to set options

    def __len__(self) -> int:
        base = len(self.all_options)

        if base <= 25:
            return 1

        elif base <= 48:
            return 2

        full, part = divmod(base - 48, 23)

        return 2 + full + bool(part)

    @property
    def page(self) -> int:
        """Current page of options"""
        return self._page

    @page.setter
    def page(self, page: int) -> None:
        self._page = int(page)

        if len(self) == 1:
            self._underlying.options = self.all_options

        elif self.page == 0:
            self._underlying.options = self.all_options[:24] + [self.down]

        elif self.page == len(self) - 1:
            self._underlying.options = [self.up] + self.all_options[self.page * 23 + 1 :]

        else:
            self._underlying.options = [
                x
                for y in (
                    (self.up,),
                    self.all_options[self.page * 23 + 1 : self.page * 23 + 24],
                    (self.down,),
                )
                for x in y
            ]

    @property
    def options(self) -> list[SelectOption]:
        """All underlying `SelectOption`s"""
        return self.all_options

    @options.setter
    def options(self, new: list[SelectOption]) -> None:
        self.all_options = new
        self.page = 0

    def check_option(self, option_id: str) -> bool:
        if option_id == self.up.value:
            self.page -= 1
            return True

        elif option_id == self.down.value:
            self.page += 1
            return True

        return False
