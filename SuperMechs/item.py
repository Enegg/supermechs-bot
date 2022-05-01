from __future__ import annotations

import typing as t
from dataclasses import dataclass, InitVar, field
from typing_extensions import Self

from utils import js_format

from .enums import Element, Icon, RarityRange
from .images import get_image
from .types import (
    AnyStats,
    Attachment,
    Attachments,
    AttachmentType,
    PackConfig,
    ItemDict,
)

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL.Image import Image


@dataclass(slots=True)
class Item(t.Generic[AttachmentType]):
    """Represents a single item."""

    id: int
    name: str
    pack: PackConfig
    image_url: str
    icon: Icon
    rarity: RarityRange
    stats: AnyStats
    element: Element = Element.OMNI
    attachment: AttachmentType = t.cast(AttachmentType, None)

    width: InitVar[int] = 0
    height: InitVar[int] = 0
    extra: dict[str, t.Any] = field(default_factory=dict)
    _image: Image | None = field(default=None, init=False, repr=False)
    _image_resize: tuple[int, int] = field(init=False, repr=False)

    def __post_init__(self, width: int, height: int) -> None:
        self.image_url = js_format(self.image_url, url=self.pack["base_url"])
        self._image_resize = (width, height)

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash((self.id, self.name, self.type, self.rarity, self.element, self.pack["key"]))

    @property
    def type(self) -> str:
        return self.icon.name

    @property
    def displayable(self) -> bool:
        """Returns True if the item can be rendered on the mech, False otherwise"""
        return self.type not in {"TELE", "CHARGE", "HOOK", "MODULE"}

    @property
    def image(self) -> Image:
        """Returns the `PIL.Image.Image` object for this item.
        Before this property is ever retrieved, `load_image` must be called."""
        if self._image is None:
            raise RuntimeError("load_image was never called")

        return self._image

    @property
    def has_image(self) -> bool:
        """Whether item has image cached."""
        return self._image is not None

    async def load_image(self, session: ClientSession, /, *, force: bool = False) -> None:
        """Loads the image from web

        Parameters
        -----------
        session:
            the session to perform the image request with.
        force:
            if true and item has an image cached, it will be overwritten."""
        if self.has_image and not force:
            return

        raw = await get_image(self.image_url, session)

        new_width, new_height = self._image_resize

        if new_width or new_height:
            width = new_width or raw.width
            height = new_height or raw.height

            self._image = raw.convert("RGBA").resize((width, height))

        else:
            self._image = raw.convert("RGBA")

    @classmethod
    def from_json(cls, json: ItemDict, pack: PackConfig) -> Self:
        return cls(
            id=json.pop("id"),
            name=json.pop("name"),
            pack=pack,
            image_url=json.pop("image"),
            icon=Icon[json.pop("type").upper()],
            rarity=RarityRange.from_string(json.pop("transform_range")),
            stats=json.pop("stats"),
            element=Element[json.pop("element")],
            attachment=json.pop("attachment", None),  # type: ignore
            extra=t.cast(dict, json),
        )


AnyItem = Item[Attachment] | Item[Attachments] | Item[None]
