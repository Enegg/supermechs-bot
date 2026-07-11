from collections import abc
from typing import Final

import supermechs.all as sm
from supermechs import arenashop
from supermechs.stats import AnyBonus, FlatBonus, MultiplierBonus

ARENA_BONUSES: Final = sm.ArenaShop[abc.Sequence[AnyBonus]](
    energy_capacity     =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    energy_regeneration =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    energy_damage       =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    heat_capacity       =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    heat_cooling        =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    heat_damage         =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    physical_damage     =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    explosive_damage    =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    electric_damage     =MultiplierBonus.from_percentages(0,  1,  3,  5,  7,  9,  11,  13,  15,  17,  20),
    physical_resistance =MultiplierBonus.from_percentages(0,  2,  6, 10, 14, 18,  22,  26,  30,  34,  40),
    explosive_resistance=MultiplierBonus.from_percentages(0,  2,  6, 10, 14, 18,  22,  26,  30,  34,  40),
    electric_resistance =MultiplierBonus.from_percentages(0,  2,  6, 10, 14, 18,  22,  26,  30,  34,  40),
    fuel_capacity       =FlatBonus.from_values(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
    fuel_regeneration   =MultiplierBonus.from_percentages(0, 1, 3,  5,  7,  9, 11, 13, 15, 17, 20, 23),
    total_hp            =FlatBonus.from_values(0, 10, 30, 60, 90, 120, 150, 180, 220, 260, 300, 350),
    damage_vs_titans    =MultiplierBonus.from_percentages(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
    backfire_reduction  =MultiplierBonus.from_percentages(0, -1, -3, -5, -7, -9, -11, -13, -15, -17, -20),
)  # fmt: skip
MAXED_ARENA_SHOP: Final[arenashop.ArenaShopLevels] = sm.ArenaShop.maxed(ARENA_BONUSES)
MAXED_ARENA_BUFFS: Final[arenashop.ArenaShop[AnyBonus]] = arenashop.bind_levels(
    MAXED_ARENA_SHOP, ARENA_BONUSES
)
