import math
from collections import abc
from typing import Protocol, Self

import attrs

from dupermechs.arenashop import IArenaShop
from dupermechs.enums import ItemStat, MechStat

__all__ = (
    "AnyBonus",
    "FlatBonus",
    "IItemStats",
    "IMechStats",
    "ItemStats",
    "MultiplierBonus",
    "bonus_damage_vs_titan",
    "bonus_item_stats",
    "bonus_mech_stats",
    "combine",
    "overload_hp_penalty",
)


class IMechStats(Protocol):
    @property
    def weight(self) -> int: ...
    @property
    def hit_points(self) -> int: ...
    @property
    def energy_capacity(self) -> int: ...
    @property
    def energy_regeneration(self) -> int: ...
    @property
    def heat_capacity(self) -> int: ...
    @property
    def heat_cooling(self) -> int: ...
    @property
    def physical_resistance(self) -> int: ...
    @property
    def explosive_resistance(self) -> int: ...
    @property
    def electric_resistance(self) -> int: ...
    @property
    def bullets_capacity(self) -> int: ...
    @property
    def rockets_capacity(self) -> int: ...

    def __getitem__(self, stat: MechStat, /) -> int: ...
    def __replace__(
        self,
        *,
        weight: int = ...,
        hit_points: int = ...,
        energy_capacity: int = ...,
        energy_regeneration: int = ...,
        heat_capacity: int = ...,
        heat_cooling: int = ...,
        physical_resistance: int = ...,
        explosive_resistance: int = ...,
        electric_resistance: int = ...,
        bullets_capacity: int = ...,
        rockets_capacity: int = ...,
    ) -> Self: ...


class IItemStats(Protocol):
    @property
    def weight(self) -> int: ...
    @property
    def hit_points(self) -> int: ...
    @property
    def energy_capacity(self) -> int: ...
    @property
    def energy_regeneration(self) -> int: ...
    @property
    def heat_capacity(self) -> int: ...
    @property
    def heat_cooling(self) -> int: ...
    @property
    def physical_resistance(self) -> int: ...
    @property
    def explosive_resistance(self) -> int: ...
    @property
    def electric_resistance(self) -> int: ...
    @property
    def bullets_capacity(self) -> int: ...
    @property
    def rockets_capacity(self) -> int: ...
    @property
    def walk(self) -> int: ...
    @property
    def jump(self) -> int: ...
    @property
    def physical_damage(self) -> int: ...
    @property
    def physical_damage_addon(self) -> int: ...
    @property
    def physical_resistance_damage(self) -> int: ...
    @property
    def electric_damage(self) -> int: ...
    @property
    def electric_damage_addon(self) -> int: ...
    @property
    def energy_damage(self) -> int: ...
    @property
    def energy_capacity_damage(self) -> int: ...
    @property
    def regeneration_damage(self) -> int: ...
    @property
    def electric_resistance_damage(self) -> int: ...
    @property
    def explosive_damage(self) -> int: ...
    @property
    def explosive_damage_addon(self) -> int: ...
    @property
    def heat_damage(self) -> int: ...
    @property
    def heat_capacity_damage(self) -> int: ...
    @property
    def cooling_damage(self) -> int: ...
    @property
    def explosive_resistance_damage(self) -> int: ...
    @property
    def range(self) -> int: ...
    @property
    def range_addon(self) -> int: ...
    @property
    def push(self) -> int: ...
    @property
    def pull(self) -> int: ...
    @property
    def recoil(self) -> int: ...
    @property
    def advance(self) -> int: ...
    @property
    def retreat(self) -> int: ...
    @property
    def uses(self) -> int: ...
    @property
    def backfire(self) -> int: ...
    @property
    def repair(self) -> int: ...
    @property
    def heat_generation(self) -> int: ...
    @property
    def energy_cost(self) -> int: ...
    @property
    def bullets_cost(self) -> int: ...
    @property
    def rockets_cost(self) -> int: ...

    def __getitem__(self, stat: MechStat | ItemStat, /) -> int: ...
    def __replace__(
        self,
        *,
        weight: int = ...,
        hit_points: int = ...,
        energy_capacity: int = ...,
        energy_regeneration: int = ...,
        heat_capacity: int = ...,
        heat_cooling: int = ...,
        physical_resistance: int = ...,
        explosive_resistance: int = ...,
        electric_resistance: int = ...,
        bullets_capacity: int = ...,
        rockets_capacity: int = ...,
        walk: int = ...,
        jump: int = ...,
        physical_damage: int = ...,
        physical_damage_addon: int = ...,
        physical_resistance_damage: int = ...,
        electric_damage: int = ...,
        electric_damage_addon: int = ...,
        energy_damage: int = ...,
        energy_capacity_damage: int = ...,
        regeneration_damage: int = ...,
        electric_resistance_damage: int = ...,
        explosive_damage: int = ...,
        explosive_damage_addon: int = ...,
        heat_damage: int = ...,
        heat_capacity_damage: int = ...,
        cooling_damage: int = ...,
        explosive_resistance_damage: int = ...,
        range: int = ...,  # noqa: A002
        range_addon: int = ...,
        push: int = ...,
        pull: int = ...,
        recoil: int = ...,
        advance: int = ...,
        retreat: int = ...,
        uses: int = ...,
        backfire: int = ...,
        repair: int = ...,
        heat_generation: int = ...,
        energy_cost: int = ...,
        bullets_cost: int = ...,
        rockets_cost: int = ...,
    ) -> Self: ...


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
    physical_damage: int = 0
    physical_damage_addon: int = 0
    physical_resistance_damage: int = 0
    electric_damage: int = 0
    electric_damage_addon: int = 0
    energy_damage: int = 0
    energy_capacity_damage: int = 0
    regeneration_damage: int = 0
    electric_resistance_damage: int = 0
    explosive_damage: int = 0
    explosive_damage_addon: int = 0
    heat_damage: int = 0
    heat_capacity_damage: int = 0
    cooling_damage: int = 0
    explosive_resistance_damage: int = 0
    range: int = 0
    range_addon: int = 0
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

    def __getitem__(self, stat: ItemStat | MechStat, /) -> int:
        return getattr(self, stat.name)


def combine(parts: abc.Iterable[IItemStats], /) -> ItemStats:
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
        total.physical_damage += part.physical_damage
        total.physical_damage_addon += part.physical_damage_addon
        total.physical_resistance_damage += part.physical_resistance_damage
        total.electric_damage += part.electric_damage
        total.electric_damage_addon += part.electric_damage_addon
        total.energy_damage += part.energy_damage
        total.energy_capacity_damage += part.energy_capacity_damage
        total.regeneration_damage += part.regeneration_damage
        total.electric_resistance_damage += part.electric_resistance_damage
        total.explosive_damage += part.explosive_damage
        total.explosive_damage_addon += part.explosive_damage_addon
        total.heat_damage += part.heat_damage
        total.heat_capacity_damage += part.heat_capacity_damage
        total.cooling_damage += part.cooling_damage
        total.explosive_resistance_damage += part.explosive_resistance_damage
        total.range += part.range
        total.range_addon += part.range_addon
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


def bonus_item_stats(stats: IItemStats, buffs: IArenaShop[AnyBonus]) -> ItemStats:
    return ItemStats(
        energy_capacity=buffs.energy_capacity.apply(stats.energy_capacity),
        energy_regeneration=buffs.energy_regeneration.apply(stats.energy_regeneration),
        energy_damage=buffs.energy_damage.apply(stats.energy_damage),
        heat_capacity=buffs.heat_capacity.apply(stats.heat_capacity),
        heat_cooling=buffs.heat_cooling.apply(stats.heat_cooling),
        heat_damage=buffs.heat_damage.apply(stats.heat_damage),
        physical_damage=buffs.physical_damage.apply(stats.physical_damage),
        physical_damage_addon=buffs.physical_damage.apply(stats.physical_damage_addon),
        explosive_damage=buffs.explosive_damage.apply(stats.explosive_damage),
        explosive_damage_addon=buffs.explosive_damage.apply(stats.explosive_damage_addon),
        electric_damage=buffs.electric_damage.apply(stats.electric_damage),
        electric_damage_addon=buffs.electric_damage.apply(stats.electric_damage_addon),
        physical_resistance=buffs.physical_resistance.apply(stats.physical_resistance),
        explosive_resistance=buffs.explosive_resistance.apply(stats.explosive_resistance),
        electric_resistance=buffs.electric_resistance.apply(stats.electric_resistance),
        backfire=buffs.backfire_reduction.apply(stats.backfire),
    )


def bonus_mech_stats(stats: IMechStats, buffs: IArenaShop[AnyBonus]) -> ItemStats:
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


def bonus_damage_vs_titan(stats: IItemStats, buffs: IArenaShop[AnyBonus]) -> ItemStats:
    return ItemStats(
        physical_damage=buffs.damage_vs_titans.apply(stats.physical_damage),
        physical_damage_addon=buffs.damage_vs_titans.apply(stats.physical_damage_addon),
        explosive_damage=buffs.damage_vs_titans.apply(stats.explosive_damage),
        explosive_damage_addon=buffs.damage_vs_titans.apply(stats.explosive_damage_addon),
        electric_damage=buffs.damage_vs_titans.apply(stats.electric_damage),
        electric_damage_addon=buffs.damage_vs_titans.apply(stats.electric_damage_addon),
    )


def overload_hp_penalty(weight: int, *, safe_weight: int = 1000, penalty_per_kg: int = 15) -> int:
    if weight <= safe_weight:
        return 0

    return (weight - safe_weight) * penalty_per_kg
