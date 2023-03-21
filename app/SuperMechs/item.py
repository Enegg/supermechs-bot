from __future__ import annotations

import typing as t

from attrs import field, frozen, validators
from typing_extensions import Self

from .core import AnyStats, TransformRange
from .enums import Element, Tier, Type
from .stat_handler import ItemStatsContainer
from .typedefs import ID, AnyItemDict, ItemDictVer1, ItemDictVer2, Name

__all__ = ("Item", "ItemProto", "Tags")


class ItemProto(t.Protocol):
    @property
    def id(self) -> ID:
        ...

    @property
    def pack_key(self) -> str:
        ...

    @property
    def name(self) -> Name:
        ...

    @property
    def type(self) -> Type:
        ...

    @property
    def element(self) -> Element:
        ...

    @property
    def transform_range(self) -> TransformRange:
        ...

    @property
    def stats(self) -> ItemStatsContainer:
        ...

    @property
    def tags(self) -> Tags:
        ...


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
        stats: ItemStatsContainer,
        custom: bool,
    ) -> Self:
        literal_tags = set(tags)

        if "legacy" in literal_tags:
            if transform_range.min is Tier.MYTHICAL:
                literal_tags.add("premium")

        elif transform_range.min >= Tier.LEGENDARY:
            literal_tags.add("premium")

        if stats.has_any_of_stats("advance", "retreat"):
            literal_tags.add("require_jump")

        if custom:
            literal_tags.add("custom")

        return cls.from_iterable(literal_tags)


@frozen(kw_only=True, order=False)
class Item:
    """Base item class with stats at every tier."""

    id: ID = field(validator=validators.ge(1))
    pack_key: str
    name: Name = field(validator=validators.min_len(1))
    type: Type = field(validator=validators.in_(Type), repr=str)
    element: Element = field(validator=validators.in_(Element), repr=str)
    transform_range: TransformRange
    stats: ItemStatsContainer
    tags: Tags

    @property
    def max_stats(self) -> AnyStats:
        """The max stats this item can have, excluding buffs."""
        return self.stats[self.transform_range.max].max

    @classmethod
    def from_json(
        cls,
        data: AnyItemDict,
        pack_key: str,
        custom: bool,
    ) -> Self:
        transform_range = TransformRange.from_string(data["transform_range"])

        if "stats" not in data:
            stats = ItemStatsContainer.from_json_v3(data)

        else:
            data = t.cast(ItemDictVer1 | ItemDictVer2, data)
            stats = ItemStatsContainer.from_json_v1_v2(data)

        tags = Tags.from_data(data.get("tags", ()), transform_range, stats, custom)

        self = cls(
            id=data["id"],
            pack_key=pack_key,
            name=data["name"],
            type=Type[data["type"].upper()],
            element=Element[data["element"].upper()],
            transform_range=transform_range,
            stats=stats,
            tags=tags,
        )

        return self
