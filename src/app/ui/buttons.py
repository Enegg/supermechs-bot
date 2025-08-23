from typing import Literal, override

from discord.typeshed import EmojiType
from disnake import ButtonStyle, ui

__all__ = ("ActionButton", "UrlButton")

type ActiveButtonStyle = Literal[
    ButtonStyle.primary,
    ButtonStyle.secondary,
    ButtonStyle.success,
    ButtonStyle.danger,
    ButtonStyle.blurple,
    ButtonStyle.grey,
    ButtonStyle.gray,
    ButtonStyle.green,
    ButtonStyle.red,
]


class ActionButton(ui.Button[None]):
    """Represents an interactive button."""

    def __init__(
        self,
        *,
        custom_id: str,
        style: ActiveButtonStyle = ButtonStyle.secondary,
        label: str | None = None,
        disabled: bool = False,
        emoji: EmojiType | None = None,
        id: int = 0,
    ) -> None:
        super().__init__(
            style=style, label=label, disabled=disabled, custom_id=custom_id, emoji=emoji, id=id
        )

    @property
    @override
    def custom_id(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Component's unique identifier."""
        custom_id = super().custom_id
        assert custom_id is not None
        return custom_id


class UrlButton(ui.Button[None]):
    """Represents a dummy button with a link."""

    def __init__(
        self,
        *,
        url: str,
        label: str | None = None,
        disabled: bool = False,
        emoji: EmojiType | None = None,
        id: int = 0,
    ) -> None:
        super().__init__(label=label, disabled=disabled, url=url, emoji=emoji, id=id)

    @property
    @override
    def url(self) -> str:
        """The URL this button sends you to."""
        url = super().url
        assert url is not None
        return url

    @url.setter
    def url(self, url: str) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        super().url = url
