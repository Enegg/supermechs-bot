from collections import abc
from typing import Any

import attrs

from dupermechs.enums import ArenaShopCategory

__all__ = ("ArenaShop", "ArenaShopBonuses", "ArenaShopLevels", "bind_levels")

type ArenaShopLevels = ArenaShop[int]
type ArenaShopBonuses[T] = ArenaShop[abc.Sequence[T]]


@attrs.define(kw_only=True)
class ArenaShop[T]:
    Category = ArenaShopCategory

    energy_capacity: T
    energy_regeneration: T
    energy_damage: T
    heat_capacity: T
    heat_cooling: T
    heat_damage: T
    physical_damage: T
    explosive_damage: T
    electric_damage: T
    physical_resistance: T
    explosive_resistance: T
    electric_resistance: T
    fuel_capacity: T
    fuel_regeneration: T
    total_hp: T
    damage_vs_titans: T
    backfire_reduction: T

    def __getitem__(self, category: ArenaShopCategory, /) -> T:
        return getattr(self, category.name)

    def __setitem__(self, category: ArenaShopCategory, value: T, /) -> None:
        setattr(self, category.name, value)

    @classmethod
    def zero(cls) -> ArenaShopLevels:
        return ArenaShop(
            energy_capacity=0,
            energy_regeneration=0,
            energy_damage=0,
            heat_capacity=0,
            heat_cooling=0,
            heat_damage=0,
            physical_damage=0,
            explosive_damage=0,
            electric_damage=0,
            physical_resistance=0,
            explosive_resistance=0,
            electric_resistance=0,
            fuel_capacity=0,
            fuel_regeneration=0,
            total_hp=0,
            damage_vs_titans=0,
            backfire_reduction=0,
        )

    @classmethod
    def maxed(cls, bonuses: ArenaShopBonuses[Any], /) -> ArenaShopLevels:
        return ArenaShop(
            energy_capacity=len(bonuses.energy_capacity) - 1,
            energy_regeneration=len(bonuses.energy_regeneration) - 1,
            energy_damage=len(bonuses.energy_damage) - 1,
            heat_capacity=len(bonuses.heat_capacity) - 1,
            heat_cooling=len(bonuses.heat_cooling) - 1,
            heat_damage=len(bonuses.heat_damage) - 1,
            physical_damage=len(bonuses.physical_damage) - 1,
            explosive_damage=len(bonuses.explosive_damage) - 1,
            electric_damage=len(bonuses.electric_damage) - 1,
            physical_resistance=len(bonuses.physical_resistance) - 1,
            explosive_resistance=len(bonuses.explosive_resistance) - 1,
            electric_resistance=len(bonuses.electric_resistance) - 1,
            fuel_capacity=len(bonuses.fuel_capacity) - 1,
            fuel_regeneration=len(bonuses.fuel_regeneration) - 1,
            total_hp=len(bonuses.total_hp) - 1,
            damage_vs_titans=len(bonuses.damage_vs_titans) - 1,
            backfire_reduction=len(bonuses.backfire_reduction) - 1,
        )


def bind_levels[T](levels: ArenaShopLevels, bonuses: ArenaShopBonuses[T]) -> ArenaShop[T]:
    return ArenaShop(
        energy_capacity=bonuses.energy_capacity[levels.energy_capacity],
        energy_regeneration=bonuses.energy_regeneration[levels.energy_regeneration],
        energy_damage=bonuses.energy_damage[levels.energy_damage],
        heat_capacity=bonuses.heat_capacity[levels.heat_capacity],
        heat_cooling=bonuses.heat_cooling[levels.heat_cooling],
        heat_damage=bonuses.heat_damage[levels.heat_damage],
        physical_damage=bonuses.physical_damage[levels.physical_damage],
        explosive_damage=bonuses.explosive_damage[levels.explosive_damage],
        electric_damage=bonuses.electric_damage[levels.electric_damage],
        physical_resistance=bonuses.physical_resistance[levels.physical_resistance],
        explosive_resistance=bonuses.explosive_resistance[levels.explosive_resistance],
        electric_resistance=bonuses.electric_resistance[levels.electric_resistance],
        fuel_capacity=bonuses.fuel_capacity[levels.fuel_capacity],
        fuel_regeneration=bonuses.fuel_regeneration[levels.fuel_regeneration],
        total_hp=bonuses.total_hp[levels.total_hp],
        damage_vs_titans=bonuses.damage_vs_titans[levels.damage_vs_titans],
        backfire_reduction=bonuses.backfire_reduction[levels.backfire_reduction],
    )
