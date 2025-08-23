"""Extension of the library provided UI kit."""

from functools import partial
from typing import TYPE_CHECKING

import disnake
from app.disnake_types import Interaction, MessageInteraction
from disnake import (
    ButtonStyle,
    File as _FileObject,
    MediaGalleryItem,
    SelectOption,
    SeparatorSpacing,
    TextInputStyle,
    UnfurledMediaItem,
)
from disnake.components import handle_media_item_input as _handle_media_item_input
from disnake.ui import (
    ActionRow,
    Components,
    Container,
    File,
    MediaGallery,
    MessageUIComponent,
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

from .buttons import ActionButton, UrlButton
from .selects import option_to_page_count

if TYPE_CHECKING:
    from disnake.components import MediaItemInput
    from disnake.ui.container import ContainerChildUIComponent as _ContainerChildUIComponent


__all__ = (
    "ActionButton",
    "ActionRow",
    "ButtonStyle",
    "CallbackStore",
    "Container",
    "File",
    "MediaGallery",
    "MediaGalleryItem",
    "MessageComponents",
    "MessageInteraction",
    "Modal",
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
type MessageComponents = Components[MessageUIComponent]
type ContainerChildUIComponent = _ContainerChildUIComponent
type MediaConvertible = MediaItemInput | _FileObject


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
