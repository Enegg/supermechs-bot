"""Extension of the library provided UI kit."""

from functools import partial
from typing import TYPE_CHECKING

import disnake
from app.disnake_types import Interaction, MessageInteraction
from disnake import (
    ButtonStyle,
    MediaGalleryItem,
    SelectOption,
    SeparatorSpacingSize as SeparatorSpacing,
    TextInputStyle,
)
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

from .buttons import ActionButton, ToggleButton, UrlButton
from .selects import option_to_page_count

if TYPE_CHECKING:
    from disnake.types.components import MediaGalleryItem as _MediaGalleryItemPayload
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
    "ToggleButton",
    "UrlButton",
    "callback_store",
    "media_gallery_item",
    "option_to_page_count",
    "thumbnail",
)

type CallbackStore = _CallbackStore[MessageInteraction]
type MessageComponents = Components[MessageUIComponent]
type ContainerChildUIComponent = _ContainerChildUIComponent
type MediaGalleryItemPayload = _MediaGalleryItemPayload

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


def media_gallery_item(
    url: str, *, description: str | None = None, spoiler: bool = False
) -> MediaGalleryItem:
    payload: MediaGalleryItemPayload = {"media": {"url": url}}
    if description is not None:
        payload["description"] = description
    if spoiler:
        payload["spoiler"] = True
    return MediaGalleryItem(payload)


def thumbnail(url: str, *, description: str | None = None, spoiler: bool = False) -> Thumbnail:
    return Thumbnail(media={"url": url}, description=description, spoiler=spoiler)
