from __future__ import annotations

import typing as t

from disnake import ButtonStyle
from disnake.ui.button import Button

from typeshed import T

if t.TYPE_CHECKING:
    from disnake import Emoji, PartialEmoji

__all__ = ("ToggleButton", "TrinaryButton")


class LinkButton(Button[None]):
    """Represents a dummy button with a link."""

    def __init__(
        self,
        *,
        label: str | None = None,
        disabled: bool = False,
        url: str | None = None,
        emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
    ) -> None:
        super().__init__(label=label, disabled=disabled, url=url, emoji=emoji, row=row)


class ToggleButton(Button[None]):
    """A two-state button."""

    def __init__(
        self,
        *,
        custom_id: str | None = None,
        style: ButtonStyle | None = None,
        style_off: ButtonStyle = ButtonStyle.gray,
        style_on: ButtonStyle = ButtonStyle.green,
        label: str | None = None,
        disabled: bool = False,
        emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
        on: bool = False,
    ) -> None:
        super().__init__(
            style=style or (style_on if on else style_off),
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            emoji=emoji,
            row=row,
        )
        self.style_off = style_off
        self.style_on = style_on

    @property
    def custom_id(self) -> str:
        """The ID of the button that gets received during an interaction."""
        custom_id = super().custom_id
        assert custom_id is not None
        return custom_id

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


class TrinaryButton(ToggleButton, t.Generic[T]):
    """A tri-state button."""

    NOTSET: t.Any = object()

    def __init__(
        self,
        *,
        custom_id: str | None = None,
        item: T = NOTSET,
        style: ButtonStyle | None = None,
        style_off: ButtonStyle = ButtonStyle.gray,
        style_on: ButtonStyle = ButtonStyle.blurple,
        style_item: ButtonStyle = ButtonStyle.green,
        label: str | None = None,
        disabled: bool = False,
        emoji: str | Emoji | PartialEmoji | None = None,
        row: int | None = None,
        on: bool = False,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            style=style or (style_on if on else style_item if item else style_off),
            style_off=style_off,
            style_on=style_on,
            label=label,
            disabled=disabled,
            emoji=emoji,
            row=row,
            on=on,
        )
        self.style_item = style_item
        self.item = item

    def toggle(self) -> None:
        if self.style is not self.style_on:
            self.style = self.style_on

        elif self.item is not self.NOTSET:
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
