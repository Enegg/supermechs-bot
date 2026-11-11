from collections import abc
from typing import Annotated, Literal

import msgspec


class LocaleMetadataDto(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: str | msgspec.UnsetType = msgspec.UNSET
    region: str | msgspec.UnsetType = msgspec.UNSET


class LocaleFileStruct(msgspec.Struct):
    metadata: LocaleMetadataDto
    stats: abc.Mapping[str, str]
    messages: abc.Mapping[str, str] | msgspec.UnsetType = msgspec.UNSET
    commands: abc.Mapping[str, str] | msgspec.UnsetType = msgspec.UNSET


# -------------------------------------------- item pack -------------------------------------------
type LiteralSlot = Literal[
    "TORSO",
    "LEGS",
    "DRONE",
    "SIDE_WEAPON",
    "TOP_WEAPON",
    "CHARGE_ENGINE",
    "CHARGE",
    "TELEPORTER",
    "GRAPPLING_HOOK",
    "HOOK",
    "SHIELD",
    "MODULE",
    "PERK",
    "KIT",
]
type LiteralElement = Literal["OTHER", "PHYSICAL", "EXPLOSIVE", "ELECTRIC", "COMBINED"]
type LiteralTier = Literal["COMMON", "RARE", "EPIC", "LEGENDARY", "MYTHICAL", "DIVINE", "PERK"]
type LiteralSubtype = Literal[
    "POWER_KIT",
    "COLOR_KIT",
    "TRANSFORM_RELIC",
    "ASCENSION_RELIC",
    "TORSO_PERK",
    "GIANT_PERK",
    "TINY_PERK",
    "HAT_PERK",
    "SHOTS_PERK",
    "MELEE_WEAPON",
]
type UInt = Annotated[int, msgspec.Meta(ge=0)]
type PosInt = Annotated[int, msgspec.Meta(gt=0)]
type ItemName = Annotated[str, msgspec.Meta(min_length=3, max_length=32)]
type TransformRange = Annotated[str, msgspec.Meta(pattern=r"^[crelmdCRELMD](?:-[crelmdCRELMD])?$")]


class ItemStatsDto(msgspec.Struct, kw_only=True):
    weight: int = msgspec.field(default=0, name="weight")
    hit_points: int = msgspec.field(default=0, name="health")
    heat_capacity: int = msgspec.field(default=0, name="heaCap")
    heat_cooling: int = msgspec.field(default=0, name="heaCol")
    energy_capacity: int = msgspec.field(default=0, name="eneCap")
    energy_regeneration: int = msgspec.field(default=0, name="eneReg")
    physical_resistance: int = msgspec.field(default=0, name="phyRes")
    explosive_resistance: int = msgspec.field(default=0, name="expRes")
    electric_resistance: int = msgspec.field(default=0, name="eleRes")
    bullets_capacity: int = msgspec.field(default=0, name="bulletsCap")
    rockets_capacity: int = msgspec.field(default=0, name="rocketsCap")
    walk: int = msgspec.field(default=0, name="walk")
    jump: int = msgspec.field(default=0, name="jump")
    physical_damage: tuple[int, int] = msgspec.field(default=(0, 0), name="phyDmg")
    physical_resistance_damage: int = msgspec.field(default=0, name="phyResDmg")
    explosive_damage: tuple[int, int] = msgspec.field(default=(0, 0), name="expDmg")
    explosive_resistance_damage: int = msgspec.field(default=0, name="expResDmg")
    heat_damage: int = msgspec.field(default=0, name="heaDmg")
    heat_capacity_damage: int = msgspec.field(default=0, name="heaCapDmg")
    heat_cooling_damage: int = msgspec.field(default=0, name="heaColDmg")
    electric_damage: tuple[int, int] = msgspec.field(default=(0, 0), name="eleDmg")
    electric_resistance_damage: int = msgspec.field(default=0, name="eleResDmg")
    energy_damage: int = msgspec.field(default=0, name="eneDmg")
    energy_capacity_damage: int = msgspec.field(default=0, name="eneCapDmg")
    energy_regeneration_damage: int = msgspec.field(default=0, name="eneRegDmg")
    range: tuple[int, int] = msgspec.field(default=(0, 0), name="range")
    push: int = msgspec.field(default=0, name="push")
    pull: int = msgspec.field(default=0, name="pull")
    recoil: int = msgspec.field(default=0, name="recoil")
    advance: int = msgspec.field(default=0, name="advance")
    retreat: int = msgspec.field(default=0, name="retreat")
    uses: int = msgspec.field(default=0, name="uses")
    backfire: int = msgspec.field(default=0, name="backfire")
    repair: int = msgspec.field(default=0, name="repair")
    heat_generation: int = msgspec.field(default=0, name="heaCost")
    energy_cost: int = msgspec.field(default=0, name="eneCost")
    bullets_cost: int = msgspec.field(default=0, name="bulletsCost")
    rockets_cost: int = msgspec.field(default=0, name="rocketsCost")
    absorb_ratio: int = msgspec.field(default=0, name="absorb")
    hp_per_block: int = msgspec.field(default=0, name="hpPerBlock")
    heat_per_block: int = msgspec.field(default=0, name="heaPerBlock")
    energy_per_block: int = msgspec.field(default=0, name="enePerBlock")


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
    name: ItemName
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


class SpriteDto(msgspec.Struct, omit_defaults=True):
    gfx: str
    image: str
    # joint
    reloaded: bool = False


class GfxPackDto(msgspec.Struct):
    base_url: str
    sprites: abc.Sequence[SpriteDto]
