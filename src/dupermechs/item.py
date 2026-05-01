import datetime as dt
from collections import abc
from typing import NewType

import attrs

from dupermechs.enums import ItemElement, ItemRarity, ItemSlot, ItemSubtype
from dupermechs.stats import ItemStats

__all__ = ("Item", "ItemId", "ItemStage", "StageLevel")

ItemId = NewType("ItemId", int)


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
