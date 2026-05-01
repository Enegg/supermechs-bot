from typing import Annotated, Literal

import msgspec

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
type UInt = Annotated[int, msgspec.Meta(ge=0)]
type PosInt = Annotated[int, msgspec.Meta(gt=0)]
type Name = Annotated[str, msgspec.Meta(min_length=3, max_length=32)]
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
