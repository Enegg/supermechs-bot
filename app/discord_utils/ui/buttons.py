import typing_extensions as typing_

from disnake.enums import ButtonStyle
from disnake.ui.button import Button
from disnake.utils import MISSING

from ..typeshed import EmojiType
from .helpers import random_str

__all__ = ("ActionButton", "ToggleButton", "UrlButton")


class ActionButton(Button[None]):
    """Represents an interactive button."""

    def __init__(
        self,
        *,
        custom_id: str = MISSING,
        style: ButtonStyle = ButtonStyle.secondary,
        label: str | None = None,
        disabled: bool = False,
        emoji: EmojiType | None = None,
    ) -> None:
        if custom_id is MISSING:
            custom_id = random_str()
        super().__init__(
            style=style, label=label, disabled=disabled, custom_id=custom_id, emoji=emoji
        )

    @property
    @typing_.override
    def custom_id(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Component's unique identifier."""
        custom_id = super().custom_id
        assert custom_id is not None
        return custom_id


class UrlButton(Button[None]):
    """Represents a dummy button with a link."""

    def __init__(
        self,
        *,
        url: str,
        label: str | None = None,
        disabled: bool = False,
        emoji: EmojiType | None = None,
    ) -> None:
        super().__init__(label=label, disabled=disabled, url=url, emoji=emoji)

    @property
    @typing_.override
    def url(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The URL this button sends you to."""
        url = super().url
        assert url is not None
        return url


class ToggleButton(ActionButton):
    """A bi-state button."""

    def __init__(
        self,
        *,
        custom_id: str = MISSING,
        style_off: ButtonStyle = ButtonStyle.gray,
        style_on: ButtonStyle = ButtonStyle.green,
        label: str | None = None,
        disabled: bool = False,
        emoji: EmojiType | None = None,
        on: bool = False,
    ) -> None:
        super().__init__(
            style=(style_on if on else style_off),
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            emoji=emoji,
        )
        self.style_off = style_off
        self.style_on = style_on

    @property
    def on(self) -> bool:
        """Whether the button is currently on."""
        return self.style is self.style_on

    @on.setter
    def on(self, value: bool) -> None:
        self.style = self.style_on if value else self.style_off

    def toggle(self) -> None:
        """Toggles the state of the button between on and off."""
        self.on ^= True
