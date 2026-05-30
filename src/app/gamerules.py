from collections import abc
from typing import Final

import msgspec

from app import paths

import dupermechs.all as sm
from dupermechs import arenashop
from dupermechs.stats import AnyBonus, FlatBonus, MultiplierBonus


class _PercentBuffDto(msgspec.Struct, tag_field="type", tag="%"):
    values: abc.Sequence[int]


class _FlatBuffDto(msgspec.Struct, tag_field="type", tag="+"):
    values: abc.Sequence[int]


type _AnyBuffDto = _FlatBuffDto | _PercentBuffDto
type _ArenaBuffsDto = sm.ArenaShop[_AnyBuffDto]


def _convert_bonus(bonus: _AnyBuffDto, /) -> abc.Sequence[AnyBonus]:
    match bonus:
        case _FlatBuffDto(values):
            return FlatBonus.from_values(*values)

        case _PercentBuffDto(values):
            return MultiplierBonus.from_percentages(*values)


def _load_arena_buffs() -> arenashop.ArenaShopBonuses[AnyBonus]:
    raw = paths.BUFFS_TOML.read_bytes()
    dto: _ArenaBuffsDto = msgspec.toml.decode(raw, type=_ArenaBuffsDto)

    return sm.ArenaShop(
        energy_capacity=_convert_bonus(dto.energy_capacity),
        energy_regeneration=_convert_bonus(dto.energy_regeneration),
        energy_damage=_convert_bonus(dto.energy_damage),
        heat_capacity=_convert_bonus(dto.heat_capacity),
        heat_cooling=_convert_bonus(dto.heat_cooling),
        heat_damage=_convert_bonus(dto.heat_damage),
        physical_damage=_convert_bonus(dto.physical_damage),
        explosive_damage=_convert_bonus(dto.explosive_damage),
        electric_damage=_convert_bonus(dto.electric_damage),
        physical_resistance=_convert_bonus(dto.physical_resistance),
        explosive_resistance=_convert_bonus(dto.explosive_resistance),
        electric_resistance=_convert_bonus(dto.electric_resistance),
        fuel_capacity=_convert_bonus(dto.fuel_capacity),
        fuel_regeneration=_convert_bonus(dto.fuel_regeneration),
        total_hp=_convert_bonus(dto.total_hp),
        damage_vs_titans=_convert_bonus(dto.damage_vs_titans),
        backfire_reduction=_convert_bonus(dto.backfire_reduction),
    )


ARENA_BONUSES: Final = _load_arena_buffs()
MAXED_ARENA_SHOP: Final[arenashop.ArenaShopLevels] = sm.ArenaShop.maxed(ARENA_BONUSES)
MAXED_ARENA_BUFFS: Final[arenashop.ArenaShop[AnyBonus]] = arenashop.bind_levels(
    MAXED_ARENA_SHOP, ARENA_BONUSES
)
