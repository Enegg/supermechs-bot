from __future__ import annotations

import asyncio
import typing as t

from disnake import ButtonStyle
from disnake.ui.button import Button, V
from disnake.ui.item import DecoratedItem
from typing_extensions import Self
from lib_helpers import MessageInteraction
from utils import MISSING, no_op

B = t.TypeVar("B", bound=Button, covariant=True)
P = t.ParamSpec("P")
T = t.TypeVar("T")


class Object(t.Protocol[B, P]):
    def __init__(*args: P.args, **kwargs: P.kwargs) -> None:
        ...


ItemCallbackType = t.Callable[[t.Any, B, MessageInteraction], t.Coroutine[t.Any, t.Any, t.Any]]
Callback = t.Callable[[B, MessageInteraction], t.Coroutine[t.Any, t.Any, None]]

__all__ = ("button", "Button", "ToggleButton", "TrinaryButton", "B")


def button(
    cls: type[Object[B, P]] = Button, *_: P.args, **kwargs: P.kwargs
) -> t.Callable[[ItemCallbackType[B]], DecoratedItem[B]]:
    """A decorator that works like `disnake.ui.button`,
    but allows for custom Button subclasses."""

    def decorator(func: ItemCallbackType[B]) -> DecoratedItem[B]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("button callback must be a coroutine function")

        func.__discord_ui_model_type__ = cls
        func.__discord_ui_model_kwargs__ = kwargs
        return t.cast(DecoratedItem[B], func)

    return decorator


class ToggleButton(Button[V]):
    """A two-state button."""

    custom_id: str
    view: V

    def __init__(
        self,
        *,
        style_off: ButtonStyle = ButtonStyle.secondary,
        style_on: ButtonStyle = ButtonStyle.success,
        callback: Callback[Self] = no_op,
        on: bool = False,
        **kwargs: t.Any,
    ) -> None:
        kwargs.setdefault("style", style_on if on else style_off)
        super().__init__(**kwargs)
        self.style_off = style_off
        self.style_on = style_on
        self.call = callback

    def toggle(self) -> None:
        """Toggles the state of the button between on and off."""
        self.style = self.style_on if self.style is self.style_off else self.style_off

    @property
    def on(self) -> bool:
        """Whether the button is currently on."""
        return self.style is self.style_on

    @on.setter
    def on(self, value: bool) -> None:
        self.style = self.style_on if value else self.style_off

    async def callback(self, inter: MessageInteraction) -> None:
        await self.call(self, inter)


class TrinaryButton(ToggleButton[V], t.Generic[V, T]):
    """A tri-state button."""

    item: T

    def __init__(
        self,
        *,
        item: T = MISSING,
        style_off: ButtonStyle = ButtonStyle.gray,
        style_on: ButtonStyle = ButtonStyle.primary,
        style_item: ButtonStyle = ButtonStyle.success,
        on: bool = False,
        **kwargs: t.Any,
    ) -> None:
        kwargs.setdefault("style", style_on if on else style_item if item else style_off)
        super().__init__(**kwargs, style_on=style_on, style_off=style_off, on=on)
        self.style_item = style_item
        self.item = item

    def toggle(self) -> None:
        if self.style is not self.style_on:
            self.style = self.style_on

        elif self.item is not None:
            self.style = self.style_item

        else:
            self.style = self.style_off

    @property
    def on(self) -> bool:
        """Whether the button is currently on."""
        return self.style is self.style_on

    @on.setter
    def on(self, value: bool) -> None:
        self.style = self.style_on if value else self.style_item if self.item else self.style_off
