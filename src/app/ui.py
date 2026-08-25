"""Extension of the library provided UI kit."""

from collections import abc
from typing import TYPE_CHECKING, Literal, override

import yarl

from app.disnake_types import MessageInteraction, ModalInteraction
from discord import ComponentLimits, EmojiType
from disnake import (
    ButtonStyle,
    Color,
    File as _FileObject,
    GroupOption,
    MediaGalleryItem,
    SelectOption,
    SeparatorSpacing,
    TextInputStyle,
    UnfurledMediaItem,
)
from disnake.components import handle_media_item_input as _handle_media_item_input
from disnake.ui import (
    ActionRow,
    Button as _Button,
    Checkbox,
    CheckboxGroup,
    Container,
    File,
    FileUpload,
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

if TYPE_CHECKING:
    from disnake.components import MediaItemInput
    from disnake.ui._types import MessageComponents as _MessageComponents
    from disnake.ui.container import ContainerChildUIComponent as _ContainerChildUIComponent

__all__ = (
    "ActionButton",
    "ActionRow",
    "ButtonStyle",
    "Checkbox",
    "CheckboxGroup",
    "Container",
    "File",
    "FileUpload",
    "GroupOption",
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
    "container",
    "file",
    "get_options_slice_for_page",
    "media_gallery_item",
    "option_to_page_count",
    "thumbnail",
)

type MessageComponents = _MessageComponents
type MediaConvertible = MediaItemInput | _FileObject | yarl.URL
type ActionButtonStyle = Literal[
    ButtonStyle.primary,
    ButtonStyle.secondary,
    ButtonStyle.success,
    ButtonStyle.danger,
]
type ContainerChild = _ContainerChildUIComponent


def container(
    *components: ContainerChild,
    accent_color: Color | None = None,
    spoiler: bool = False,
    id: int = 0,
) -> tuple[Container, abc.Callable[[ContainerChild], None]]:
    container = Container(*components, accent_colour=accent_color, spoiler=spoiler, id=id)
    return container, container.children.append


def _media(media: MediaConvertible, /) -> UnfurledMediaItem:
    if isinstance(media, _FileObject):
        assert media.filename is not None
        return UnfurledMediaItem(f"attachment://{media.filename}")

    if isinstance(media, yarl.URL):
        return UnfurledMediaItem(str(media))

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


def option_to_page_count(option_count: int, /) -> int:
    if option_count <= ComponentLimits.string_select_options:
        return 1

    first_and_last_page = (ComponentLimits.string_select_options - 1) * 2

    if option_count <= first_and_last_page:
        # fits on two pages, add one of up/down option on each
        return 2

    middle_page_size = ComponentLimits.string_select_options - 2
    return 2 + (option_count - first_and_last_page + middle_page_size - 1) // middle_page_size


def option_index_to_page(option_count: int, option_index: int) -> int:
    if option_count <= ComponentLimits.string_select_options:
        return 1

    end_page_size = ComponentLimits.string_select_options - 1

    if option_index < end_page_size:
        return 1

    if option_count <= end_page_size * 2:
        return 2

    option_index -= end_page_size - 1
    middle_pages, rem = divmod(option_index, ComponentLimits.string_select_options - 2)

    return middle_pages + (rem > 0) + 1


def get_options_slice_for_page(option_count: int, page_index: int) -> tuple[int, int]:
    if option_count <= ComponentLimits.string_select_options:
        return 0, option_count

    end_page_size = ComponentLimits.string_select_options - 1

    if page_index == 0:
        return 0, end_page_size

    if option_count <= end_page_size * 2:
        return end_page_size, option_count

    middle_page_size = ComponentLimits.string_select_options - 2
    middle_page_count = (
        option_count - end_page_size * 2 + middle_page_size - 1
    ) // middle_page_size

    offset = end_page_size + middle_page_size * (page_index - 1)

    if page_index <= middle_page_count:
        return offset, offset + middle_page_size

    return offset, option_count


class ActionButton(_Button[None]):
    """Represents an interactive button."""

    def __init__(
        self,
        *,
        custom_id: str,
        style: ActionButtonStyle = ButtonStyle.secondary,
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


class UrlButton(_Button[None]):
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
