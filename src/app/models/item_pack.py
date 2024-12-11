from collections import abc
from typing import ClassVar, NewType

import attrs
from monads.option import Null, Option

from app import paths
from app.class_utils import limited_repr

from .graphics import (
    CacheImage,
    ImageRequest,
    LoadedSprite,
    PendingSprite,
    Sprite,
    SpriteKey,
    read_image,
)

from supermechs.all import ItemData, abc as smabc

__all__ = ("ItemPack", "PackKey")

PackKey = NewType("PackKey", str)


@attrs.define(kw_only=True)
class ItemPack:
    """Mapping-like container of items and their graphics."""

    missing_image: ClassVar[ImageRequest] = ImageRequest(
        str(paths.SILHOUETTE), CacheImage(read_image)
    )

    key: PackKey
    name: Option[str] = Null.null
    description: Option[str] = Null.null
    url: str | None = None

    items: abc.Mapping[smabc.ItemID, ItemData] = attrs.field(factory=dict, repr=limited_repr)
    image_requests: abc.MutableMapping[SpriteKey, ImageRequest] = attrs.field(
        factory=dict, repr=limited_repr
    )
    loaded_images: abc.MutableMapping[SpriteKey, LoadedSprite] = attrs.field(
        factory=dict, repr=limited_repr
    )

    def get_item(self, item_id: smabc.ItemID, /) -> ItemData:
        """Lookup an item by its ID."""
        return self.items[item_id]

    def get_sprite(self, item_id: smabc.ItemID, /, tier: smabc.StageTier) -> Sprite:
        """Lookup item's sprite."""
        key = (item_id, tier)

        sprite = self.loaded_images.get(key)

        if sprite is not None:
            return sprite

        request = self.image_requests.pop(key, self.missing_image)
        return PendingSprite(request, key, self.loaded_images.__setitem__)
