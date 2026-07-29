import datetime as dt
from collections import abc
from typing import NewType

import attrs

from supermechs.enums import ItemElement, ItemRarity, ItemSlot, ItemSubtype
from supermechs.stats import ItemStats

__all__ = ("Item", "ItemId", "ItemStage", "StageLevel")

ItemId = NewType("ItemId", int)


@attrs.define(kw_only=True)
class StageLevel:
    level: int = 0
    power_required: int = 0
    power_contribution: int = 0
    upgrade_gold_cost: int = 0
    stats: ItemStats = attrs.Factory(ItemStats)


@attrs.define(kw_only=True)
class ItemStage:
    Level = StageLevel

    tier: ItemRarity
    levels: abc.Sequence[StageLevel]
    evolution_gold_cost: int = 0
    ascension_gold_cost: int = 0


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
