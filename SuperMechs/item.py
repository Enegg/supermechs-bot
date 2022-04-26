from __future__ import annotations

import typing as t

from utils import js_format

from .enums import Element, Icon, RarityRange
from .images import get_image, get_image_size
from .types import AnyStats, Attachment, Attachments, AttachmentType, PackConfig

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL.Image import Image


class Item(t.Generic[AttachmentType]):
    """Represents a single item."""

    def __init__(
        self,
        *,
        id: int,
        name: str,
        image: str,
        type: str,
        stats: AnyStats,
        transform_range: str,
        pack: PackConfig,
        divine: AnyStats | None = None,
        element: str = "OMNI",
        attachment: AttachmentType = t.cast(AttachmentType, None),
        **extra: t.Any,
    ) -> None:

        self.id = id
        self.name = str(name)

        self.image_url = js_format(image, url=pack["base_url"])
        self.pack = pack
        self._image: Image | None = None
        self._cached: Image | None = None

        # this will also validate if type is of correct type
        self.icon = Icon[type.upper()]
        self.stats = stats
        self.divine = divine

        self.rarity = RarityRange.from_string(transform_range)
        self.element = Element[element]

        self.attachment = attachment
        self.extra = extra

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self.name!r}: element={self.element.name}"
            f" type={self.type} rarity={self.rarity!r} stats={self.stats}>"
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, type(self)):
            return False

        return (
            o.id == self.id
            and o.image_url == self.image_url
            and o.name == self.name
            and o.type == self.type
            and o.stats == self.stats
            and o.divine == self.divine
            and o.rarity == self.rarity
        )

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
        """Returns a copy of image for this item.
        Before this property is ever retrieved, load_image has to be called."""
        if self._image is None:
            raise RuntimeError("load_image was never called")

        if self._cached is not None:
            return self._cached

        if "width" in self.extra or "height" in self.extra:
            new_width = self.extra.get("width", 0)
            new_height = self.extra.get("height", 0)

            width, height = get_image_size(self._image)
            width = new_width or width
            height = new_height or height

            self._cached = self._image.resize((width, height))
            return self._cached

        self._cached = self._image.copy()
        return self._cached

    @image.deleter
    def image(self) -> None:
        self._cached = None

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

        if self.image_url is None:
            raise ValueError("Image URL was not set")

        self._image = await get_image(self.image_url, session)


AnyItem = Item[Attachment] | Item[Attachments] | Item[None]
