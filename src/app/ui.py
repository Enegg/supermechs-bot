"""Extension of the library provided UI kit."""

from functools import partial
from typing import TYPE_CHECKING, Literal, override

import disnake
from app.disnake_types import Interaction, MessageInteraction, ModalInteraction
from discord import ComponentLimits, EmojiType
from disnake import (
    ButtonStyle,
    File as _FileObject,
    MediaGalleryItem,
    SelectOption,
    SeparatorSpacing,
    TextInputStyle,
    UnfurledMediaItem,
    ui,
)
from disnake.components import handle_media_item_input as _handle_media_item_input
from disnake.ui import (
    ActionRow,
    Container,
    File,
    Label,
    MediaGallery,
    Modal,
    Section,
    Separator,
    StringSelect,
    TextDisplay,
    TextInput,
    Thumbnail,
)
from ui_store import CallbackStore as _CallbackStore

from app import i18n

if TYPE_CHECKING:
    from disnake.components import MediaItemInput
    from disnake.ui._types import MessageComponents as _MessageComponents
    from disnake.ui.container import ContainerChildUIComponent as _ContainerChildUIComponent


__all__ = (
    "ActionButton",
    "ActionRow",
    "ButtonStyle",
    "CallbackStore",
    "Container",
    "File",
    "Label",
    "MediaGallery",
    "MediaGalleryItem",
    "MessageComponents",
    "MessageInteraction",
    "Modal",
    "ModalInteraction",
    "Section",
    "SelectOption",
    "Separator",
    "SeparatorSpacing",
    "StringSelect",
    "TextDisplay",
    "TextInput",
    "TextInputStyle",
    "Thumbnail",
    "UrlButton",
    "callback_store",
    "file",
    "media_gallery_item",
    "option_to_page_count",
    "thumbnail",
)

type CallbackStore = _CallbackStore[MessageInteraction]
type MessageComponents = _MessageComponents
type ContainerChildUIComponent = _ContainerChildUIComponent
type MediaConvertible = MediaItemInput | _FileObject
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


def callback_store(base_inter: Interaction, /) -> CallbackStore:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == base_inter.author.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return _CallbackStore(
        partial(base_inter.bot.wait_for, disnake.Event.message_interaction), check=interaction_check
    )


def _media(media: MediaConvertible, /) -> UnfurledMediaItem:
    if isinstance(media, _FileObject):
        assert media.filename is not None
        media = f"attachment://{media.filename}"

    return _handle_media_item_input(media)


def media_gallery_item(
    media: MediaConvertible, description: str | None = None, *, spoiler: bool = False
) -> MediaGalleryItem:
    return MediaGalleryItem(media=_media(media), description=description, spoiler=spoiler)


def thumbnail(
    media: MediaConvertible, description: str | None = None, *, spoiler: bool = False, id: int = 0
) -> Thumbnail:
    return Thumbnail(media=_media(media), description=description, spoiler=spoiler, id=id)


def file(media: MediaConvertible, *, spoiler: bool = False, id: int = 0) -> File:
    return File(file=_media(media), spoiler=spoiler, id=id)


def option_to_page_count(options: int, /) -> int:
    if options <= ComponentLimits.select_options:
        return 1

    first_and_last_page = (ComponentLimits.select_options - 1) * 2

    if options <= first_and_last_page:
        # fits on two pages, add one of up/down option on each
        return 2

    size = ComponentLimits.select_options - 2
    return 2 + (options - first_and_last_page + size - 1) // size


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
