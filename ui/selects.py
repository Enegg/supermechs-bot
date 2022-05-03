from __future__ import annotations

import asyncio
import typing as t

from disnake import SelectOption
from disnake.ui.item import DecoratedItem
from disnake.ui.select import Select, V
from disnake.utils import MISSING as D_MISSING
from lib_helpers import MessageInteraction
from utils import MISSING, no_op

S = t.TypeVar("S", bound=Select, covariant=True)
P = t.ParamSpec("P")


class Object(t.Protocol[S, P]):
    def __init__(*args: P.args, **kwargs: P.kwargs) -> None:
        ...


ItemCallbackType = t.Callable[[t.Any, S, MessageInteraction], t.Coroutine[t.Any, t.Any, t.Any]]

EMPTY_OPTION: t.Final = SelectOption(label="empty", description="Select to remove", emoji="🗑️")

__all__ = ("select", "Select", "PaginatedSelect", "S", "EMPTY_OPTION")


def select(
    cls: type[Object[S, P]] = Select, *_: P.args, **kwargs: P.kwargs
) -> t.Callable[[ItemCallbackType[S]], DecoratedItem[S]]:
    """A decorator that works like `disnake.ui.select`,
    but allows for custom Select subclasses."""

    def decorator(func: ItemCallbackType[S]) -> DecoratedItem[S]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("select callback must be a coroutine function")

        func.__discord_ui_model_type__ = cls
        func.__discord_ui_model_kwargs__ = kwargs
        return t.cast(DecoratedItem[S], func)

    return decorator


class PaginatedSelect(Select[V]):
    """Select which paginates options into chunks of 23-25 and registers two
    `SelectOption`s to move between chunks."""

    def __init__(
        self,
        up: SelectOption,
        down: SelectOption,
        options: list[SelectOption] = MISSING,
        *,
        custom_id: str = D_MISSING,
        placeholder: str | None = None,
        disabled: bool = False,
        row: int | None = None,
    ) -> None:
        super().__init__(custom_id=custom_id, placeholder=placeholder, disabled=disabled, row=row)
        self.all_options = options or []
        self.up = up
        self.down = down
        self.page = 0  # calls property to set options
        self._callback = no_op

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

    @property
    def callback(self) -> t.Callable[[MessageInteraction], t.Coroutine[t.Any, t.Any, None]]:
        return self.pre_invoke_callback

    @callback.setter
    def callback(
        self, func: t.Callable[[MessageInteraction], t.Coroutine[t.Any, t.Any, None]]
    ) -> None:
        self._callback = func

    async def pre_invoke_callback(self, inter: MessageInteraction) -> None:
        (option_id,) = self.values

        if option_id == self.up.value:
            self.page -= 1
            await inter.response.edit_message(view=self.view)

        elif option_id == self.down.value:
            self.page += 1
            await inter.response.edit_message(view=self.view)

        else:
            await self._callback(inter)
