import math
from collections import abc
from typing import Self

import attrs

from supermechs.arenashop import ArenaShop
from supermechs.enums import ItemStat

__all__ = (
    "AnyBonus",
    "FlatBonus",
    "ItemStats",
    "MultiplierBonus",
    "bonus_damage_vs_titan",
    "bonus_item_stats",
    "bonus_mech_stats",
    "combine",
    "overload_hp_penalty",
)


@attrs.define(kw_only=True)
class ItemStats:
    weight: int = 0
    hit_points: int = 0
    energy_capacity: int = 0
    energy_regeneration: int = 0
    heat_capacity: int = 0
    heat_cooling: int = 0
    physical_resistance: int = 0
    explosive_resistance: int = 0
    electric_resistance: int = 0
    bullets_capacity: int = 0
    rockets_capacity: int = 0
    walk: int = 0
    jump: int = 0
    physical_damage_min: int = 0
    physical_damage_max: int = 0
    physical_resistance_damage: int = 0
    electric_damage_min: int = 0
    electric_damage_max: int = 0
    energy_damage: int = 0
    energy_capacity_damage: int = 0
    regeneration_damage: int = 0
    electric_resistance_damage: int = 0
    explosive_damage_min: int = 0
    explosive_damage_max: int = 0
    heat_damage: int = 0
    heat_capacity_damage: int = 0
    cooling_damage: int = 0
    explosive_resistance_damage: int = 0
    range_min: int = 0
    range_max: int = 0
    push: int = 0
    pull: int = 0
    recoil: int = 0
    advance: int = 0
    retreat: int = 0
    uses: int = 0
    backfire: int = 0
    repair: int = 0
    heat_generation: int = 0
    energy_cost: int = 0
    bullets_cost: int = 0
    rockets_cost: int = 0
    hit_points_per_block: int = 0
    energy_per_block: int = 0
    heat_per_block: int = 0
    block_percentage: int = 0

    def __getitem__(self, stat: ItemStat, /) -> int:
        return getattr(self, stat.name)


def combine(parts: abc.Iterable[ItemStats], /) -> ItemStats:
    total = ItemStats()

    for part in parts:
        total.weight += part.weight
        total.hit_points += part.hit_points
        total.energy_capacity += part.energy_capacity
        total.energy_regeneration += part.energy_regeneration
        total.heat_capacity += part.heat_capacity
        total.heat_cooling += part.heat_cooling
        total.physical_resistance += part.physical_resistance
        total.explosive_resistance += part.explosive_resistance
        total.electric_resistance += part.electric_resistance
        total.bullets_capacity += part.bullets_capacity
        total.rockets_capacity += part.rockets_capacity
        total.walk += part.walk
        total.jump += part.jump
        total.physical_damage_min += part.physical_damage_min
        total.physical_damage_max += part.physical_damage_max
        total.physical_resistance_damage += part.physical_resistance_damage
        total.electric_damage_min += part.electric_damage_min
        total.electric_damage_max += part.electric_damage_max
        total.energy_damage += part.energy_damage
        total.energy_capacity_damage += part.energy_capacity_damage
        total.regeneration_damage += part.regeneration_damage
        total.electric_resistance_damage += part.electric_resistance_damage
        total.explosive_damage_min += part.explosive_damage_min
        total.explosive_damage_max += part.explosive_damage_max
        total.heat_damage += part.heat_damage
        total.heat_capacity_damage += part.heat_capacity_damage
        total.cooling_damage += part.cooling_damage
        total.explosive_resistance_damage += part.explosive_resistance_damage
        total.range_min += part.range_min
        total.range_max += part.range_max
        total.push += part.push
        total.pull += part.pull
        total.recoil += part.recoil
        total.advance += part.advance
        total.retreat += part.retreat
        total.uses += part.uses
        total.backfire += part.backfire
        total.repair += part.repair
        total.heat_generation += part.heat_generation
        total.energy_cost += part.energy_cost
        total.bullets_cost += part.bullets_cost
        total.rockets_cost += part.rockets_cost
        total.hit_points_per_block += part.hit_points_per_block
        total.energy_per_block += part.energy_per_block
        total.heat_per_block += part.heat_per_block
        total.block_percentage += part.block_percentage

    return total


@attrs.frozen
class FlatBonus:
    """Bonus that adds a flat value."""

    value: int

    def apply(self, value: int | float, /) -> int:
        return self.value

    @classmethod
    def from_values(cls, *values: int) -> tuple[Self, ...]:
        return tuple(map(cls, values))


@attrs.frozen
class MultiplierBonus:
    """Bonus that multiplies a given value."""

    # anything from -0.2 to 0.005 to 0.4
    fraction: float

    def apply(self, value: int | float, /) -> int:
        return math.ceil(value * self.fraction)

    def as_percent(self) -> float:
        #  0.40  ->  40.0
        #  0.055 ->   5.5
        # -0.20  -> -20.0
        return round(self.fraction * 100.0, 1)

    @classmethod
    def from_percent(cls, percent: int | float, /) -> Self:
        return cls(round(percent / 100.0, 3))

    @classmethod
    def from_percentages(cls, *values: int | float) -> tuple[Self, ...]:
        return tuple(map(cls.from_percent, values))


type AnyBonus = FlatBonus | MultiplierBonus


def bonus_item_stats(stats: ItemStats, buffs: ArenaShop[AnyBonus]) -> ItemStats:
    return ItemStats(
        energy_capacity=buffs.energy_capacity.apply(stats.energy_capacity),
        energy_regeneration=buffs.energy_regeneration.apply(stats.energy_regeneration),
        energy_damage=buffs.energy_damage.apply(stats.energy_damage),
        heat_capacity=buffs.heat_capacity.apply(stats.heat_capacity),
        heat_cooling=buffs.heat_cooling.apply(stats.heat_cooling),
        heat_damage=buffs.heat_damage.apply(stats.heat_damage),
        physical_damage_min=buffs.physical_damage.apply(stats.physical_damage_min),
        physical_damage_max=buffs.physical_damage.apply(stats.physical_damage_max),
        explosive_damage_min=buffs.explosive_damage.apply(stats.explosive_damage_min),
        explosive_damage_max=buffs.explosive_damage.apply(stats.explosive_damage_max),
        electric_damage_min=buffs.electric_damage.apply(stats.electric_damage_min),
        electric_damage_max=buffs.electric_damage.apply(stats.electric_damage_max),
        physical_resistance=buffs.physical_resistance.apply(stats.physical_resistance),
        explosive_resistance=buffs.explosive_resistance.apply(stats.explosive_resistance),
        electric_resistance=buffs.electric_resistance.apply(stats.electric_resistance),
        backfire=buffs.backfire_reduction.apply(stats.backfire),
    )


def bonus_mech_stats(stats: ItemStats, buffs: ArenaShop[AnyBonus]) -> ItemStats:
    return ItemStats(
        energy_capacity=buffs.energy_capacity.apply(stats.energy_capacity),
        energy_regeneration=buffs.energy_regeneration.apply(stats.energy_regeneration),
        heat_capacity=buffs.heat_capacity.apply(stats.heat_capacity),
        heat_cooling=buffs.heat_cooling.apply(stats.heat_cooling),
        physical_resistance=buffs.physical_resistance.apply(stats.physical_resistance),
        explosive_resistance=buffs.explosive_resistance.apply(stats.explosive_resistance),
        electric_resistance=buffs.electric_resistance.apply(stats.electric_resistance),
        hit_points=buffs.total_hp.apply(stats.hit_points),
    )


def bonus_damage_vs_titan(stats: ItemStats, buffs: ArenaShop[AnyBonus]) -> ItemStats:
    return ItemStats(
        physical_damage_min=buffs.damage_vs_titans.apply(stats.physical_damage_min),
        physical_damage_max=buffs.damage_vs_titans.apply(stats.physical_damage_max),
        explosive_damage_min=buffs.damage_vs_titans.apply(stats.explosive_damage_min),
        explosive_damage_max=buffs.damage_vs_titans.apply(stats.explosive_damage_max),
        electric_damage_min=buffs.damage_vs_titans.apply(stats.electric_damage_min),
        electric_damage_max=buffs.damage_vs_titans.apply(stats.electric_damage_max),
    )


def overload_hp_penalty(weight: int, *, safe_weight: int = 1000, penalty_per_kg: int = 15) -> int:
    if weight <= safe_weight:
        return 0

    return (weight - safe_weight) * penalty_per_kg
