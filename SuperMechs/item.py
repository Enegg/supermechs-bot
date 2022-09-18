from __future__ import annotations

import typing as t

from attrs import field, frozen, validators
from typing_extensions import Self

from .core import TransformRange
from .enums import Element, Rarity, Type
from .game_types import AnyStats, AttachmentType
from .images import AttachedImage
from .pack_versioning import ItemDictVer1, ItemDictVer2, ItemDictVer3
from .stat_handler import StatHandler

__all__ = ("Item", "AnyItem")


@frozen
class Tags:
    premium: bool = False
    sword: bool = False
    melee: bool = False
    roller: bool = False
    legacy: bool = False
    require_jump: bool = False
    custom: bool = False

    @classmethod
    def from_iterable(cls, iterable: t.Iterable[str]) -> Self:
        return cls(**dict.fromkeys(iterable, True))


@frozen(kw_only=True, order=False)
class Item(t.Generic[AttachmentType]):
    """Base item class with stats at every tier."""

    id: int = field(validator=validators.ge(1))
    name: str = field(validator=validators.min_len(1))
    type: Type = field(validator=validators.in_(Type), repr=str)
    element: Element = field(validator=validators.in_(Element), repr=str)
    transform_range: TransformRange
    stats: StatHandler
    image: AttachedImage[AttachmentType] = field(eq=False)
    tags: Tags

    @property
    def max_stats(self) -> AnyStats:
        """The max stats this item can have, excluding buffs."""
        return self.stats.at(self.transform_range.max)

    @classmethod
    def from_json(
        cls,
        data: ItemDictVer1 | ItemDictVer2 | ItemDictVer3,
        image: AttachedImage[AttachmentType],
        custom: bool,
    ) -> Self:
        transform_range = TransformRange.from_string(data["transform_range"])

        if "stats" not in data:
            stats = StatHandler.from_new_format(data)

        else:
            data = t.cast(ItemDictVer1 | ItemDictVer2, data)
            stats = StatHandler.from_old_format(data["stats"], transform_range.max)

        tags = set[str](data.get("tags", ()))

        if ("legacy" in tags and transform_range.min is Rarity.MYTHICAL) or (
            transform_range.min > Rarity.EPIC
        ):
            tags.add("premium")

        if "advance" in stats or "retreat" in stats:
            tags.add("require_jump")

        if custom:
            tags.add("custom")

        return cls(
            id=data["id"],
            name=data["name"],
            type=Type[data["type"].upper()],
            element=Element[data["element"].upper()],
            transform_range=transform_range,
            stats=stats,
            image=image,
            tags=Tags.from_iterable(tags),
        )


AnyItem = Item[t.Any]
