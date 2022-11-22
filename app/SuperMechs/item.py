from __future__ import annotations

import typing as t

from attrs import field, frozen, validators
from typing_extensions import Self

from .core import TransformRange
from .enums import Element, Tier, Type
from .images import AttachedImage, AttachmentType
from .stat_handler import StatHandler
from .typedefs import ID, AnyItemDict, AnyStats, ItemDictVer1, ItemDictVer2, Name

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

    @classmethod
    def from_data(
        cls,
        tags: t.Iterable[str],
        transform_range: TransformRange,
        stats: StatHandler,
        custom: bool,
    ) -> Self:
        literal_tags = set(tags)

        if "legacy" not in literal_tags and transform_range.min >= Tier.LEGENDARY:
            literal_tags.add("premium")

        elif transform_range.min is Tier.MYTHICAL:
            literal_tags.add("premium")

        if "advance" in stats or "retreat" in stats:
            literal_tags.add("require_jump")

        if custom:
            literal_tags.add("custom")

        return cls.from_iterable(literal_tags)


@frozen(kw_only=True, order=False)
class Item(t.Generic[AttachmentType]):
    """Base item class with stats at every tier."""

    id: ID = field(validator=validators.ge(1))
    pack_key: str = field()
    name: Name = field(validator=validators.min_len(1))
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
        data: AnyItemDict,
        pack_key: str,
        custom: bool,
        renderer: AttachedImage[AttachmentType],
    ) -> Self:
        transform_range = TransformRange.from_string(data["transform_range"])
        item_type = Type[data["type"].upper()]

        if "stats" not in data:
            stats = StatHandler.from_new_format(data)

        else:
            data = t.cast(ItemDictVer1 | ItemDictVer2, data)
            stats = StatHandler.from_old_format(data["stats"], transform_range.max)

        width = data.get("width", 0)
        height = data.get("height", 0)

        if not width == height == 0:
            renderer.resize(width, height)

        renderer.assert_attachment()

        tags = Tags.from_data(data.get("tags", ()), transform_range, stats, custom)

        self = cls(
            id=data["id"],
            pack_key=pack_key,
            name=data["name"],
            type=item_type,
            element=Element[data["element"].upper()],
            transform_range=transform_range,
            stats=stats,
            image=renderer,
            tags=tags,
        )

        renderer.item = self
        return self


AnyItem = Item[t.Any]
