from typing import TYPE_CHECKING, Literal, override

from discord.typeshed import EmojiType
from disnake import ButtonStyle, ui

__all__ = ("ActionButton", "UrlButton")

type ActiveButtonStyle = Literal[
    ButtonStyle.primary,
    ButtonStyle.secondary,
    ButtonStyle.success,
    ButtonStyle.danger,
    # microsoft/pyright#11100
    # DisnakeDev/disnake#1473
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

    if TYPE_CHECKING:

        @property
        @override
        def custom_id(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
            """The ID of the button that gets received during an interaction."""
            ...


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

    if TYPE_CHECKING:

        @property
        @override
        def url(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
            """The URL this button sends you to."""
            ...
