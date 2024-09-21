from collections import abc
from typing import Final, TypeAlias, overload

import attrs

from app.class_utils import limited_repr

from .graphics import AbstractSprite

from supermechs.abc.item import ItemID
from supermechs.abc.item_pack import PackKey
from supermechs.api import Item, ItemData
from supermechs.enums.stats import Tier

__all__ = ("ItemPack",)

SpriteKey: TypeAlias = tuple[ItemID, Tier]


@attrs.define(kw_only=True)
class ItemPack:
    """Mapping-like container of items and their graphics."""

    key: Final[PackKey] = attrs.field()
    name: str = attrs.field(default="<no name>")
    description: str = attrs.field(default="<no description>")

    items: Final[abc.Mapping[ItemID, ItemData]] = attrs.field(repr=limited_repr.repr)
    sprites: Final[abc.Mapping[SpriteKey, AbstractSprite]] = attrs.field(repr=limited_repr.repr)

    def __contains__(self, value: ItemID | ItemData, /) -> bool:
        if isinstance(value, int):
            return value in self.items

        if isinstance(value, ItemData):
            return value.pack_key == self.key and value.id in self.items

        return False

    def get_item(self, item_id: ItemID, /) -> ItemData:
        """Lookup an item by its ID.

        Raises
        ------
        IDLookupError: item not found.
        """
        return self.items[item_id]

    @overload
    def get_sprite(self, item: Item, /) -> AbstractSprite: ...

    @overload
    def get_sprite(self, item: ItemData, /, tier: Tier) -> AbstractSprite: ...

    def get_sprite(self, item: ItemData | Item, /, tier: Tier | None = None) -> AbstractSprite:
        """Lookup item's sprite.

        Raises
        ------
        PackKeyError: item comes from different pack.
        """
        if isinstance(item, ItemData):
            if tier is None:
                msg = "Tier not provided with ItemData"
                raise TypeError(msg)

        elif tier is not None:
            msg = "Tier provided for Item"
            raise TypeError(msg)

        else:
            tier = item.tier
            item = item.data

        if item.pack_key != self.key:
            msg = f"Mismatched pack key: {item.pack_key} != {self.key}"
            raise ValueError(msg)

        return self.sprites[item.id, tier]
