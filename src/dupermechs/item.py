import datetime as dt
from collections import abc
from typing import NewType, Protocol

import attrs

from dupermechs.enums import ItemElement, ItemRarity, ItemSlot, ItemSubtype
from dupermechs.stats import IItemStats, ItemStats

__all__ = ("IItem", "IItemStage", "IStageLevel", "Item")


ItemId = NewType("ItemId", int)


class IStageLevel(Protocol):
    @property
    def level(self) -> int: ...
    @property
    def power_required(self) -> int: ...
    @property
    def power_contribution(self) -> int: ...
    @property
    def stats(self) -> IItemStats: ...


class IItemStage(Protocol):
    @property
    def tier(self) -> ItemRarity: ...
    @property
    def levels(self) -> abc.Sequence[IStageLevel]: ...


class IItem(Protocol):
    @property
    def id(self) -> ItemId: ...
    @property
    def name(self) -> str: ...
    @property
    def slot_id(self) -> ItemSlot: ...
    @property
    def element(self) -> ItemElement: ...
    @property
    def subtype(self) -> ItemSubtype: ...
    @property
    def stages(self) -> abc.Sequence[IItemStage]: ...
    @property
    def release_date(self) -> dt.datetime | None: ...


@attrs.define(kw_only=True)
class StageLevel:
    level: int = 0
    power_required: int = 0
    power_contribution: int = 0
    stats: ItemStats = attrs.Factory(ItemStats)


@attrs.define(kw_only=True)
class ItemStage:
    Level = StageLevel

    tier: ItemRarity
    levels: abc.Sequence[StageLevel]


@attrs.frozen(kw_only=True)
class Item:
    Id = ItemId
    Slot = ItemSlot
    Element = ItemElement
    Rarity = ItemRarity
    Stage = ItemStage
    Subtype = ItemSubtype

    id: ItemId
    name: str
    slot_id: ItemSlot
    element: ItemElement
    stages: abc.Sequence[ItemStage]
    subtype: ItemSubtype = ItemSubtype.none
    release_date: dt.datetime | None = None
