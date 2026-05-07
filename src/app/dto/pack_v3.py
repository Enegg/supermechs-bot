from collections import abc

import msgspec

from .common import (
    ItemStatsDto,
    LiteralElement,
    LiteralSlot,
    LiteralSubtype,
    LiteralTier,
    Name,
    PosInt,
    UInt,
)


class ItemLevelDto(msgspec.Struct, kw_only=True):
    player_level: UInt
    display_level: UInt
    upgrade_gold_cost: UInt = 0
    power_contribution: UInt = 0
    min_power_to_have: UInt = 0
    power_to_upgrade: UInt = 0
    stats: ItemStatsDto


class ItemStageDto(msgspec.Struct, kw_only=True):
    tier: LiteralTier
    image: str
    evolution_gold_cost: UInt = 0
    ascension_gold_cost: UInt = 0
    levels: abc.Sequence[ItemLevelDto]


class ItemDto(msgspec.Struct, kw_only=True):
    id: PosInt
    name: Name
    slot_id: LiteralSlot = msgspec.field(name="slot")
    element: LiteralElement
    subtype: LiteralSubtype | msgspec.UnsetType = msgspec.UNSET
    is_deprecated: bool = False
    reloaded: bool = False
    hidden: bool = False
    released_at: UInt = 0
    stages: abc.Sequence[ItemStageDto]


class ItemPackDto(msgspec.Struct, kw_only=True, tag_field="version", tag="3"):
    key: str
    name: str
    description: str
    items: abc.Sequence[ItemDto]
