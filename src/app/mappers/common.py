from collections import abc

import msgspec
from monads.option import Null, Option, Some

from app.dto.common import ItemStatsDto, LiteralElement, LiteralTier, LiteralType

import dupermechs.all as sm

type ItemMapping = abc.Mapping[sm.Item.Id, sm.Item]

LITERAL_TYPE_TO_ENUM: abc.Mapping[LiteralType, sm.Item.Type] = {
    "TORSO": sm.Item.Type.torso,
    "LEGS": sm.Item.Type.legs,
    "DRONE": sm.Item.Type.drone,
    "SIDE_WEAPON": sm.Item.Type.side_weapon,
    "TOP_WEAPON": sm.Item.Type.top_weapon,
    "CHARGE_ENGINE": sm.Item.Type.charge,
    "CHARGE": sm.Item.Type.charge,
    "TELEPORTER": sm.Item.Type.teleport,
    "GRAPPLING_HOOK": sm.Item.Type.hook,
    "HOOK": sm.Item.Type.hook,
    "SHIELD": sm.Item.Type.shield,
    "MODULE": sm.Item.Type.module,
    "PERK": sm.Item.Type.perk,
    "KIT": sm.Item.Type.kit,
}
LITERAL_ELEMENT_TO_ENUM: abc.Mapping[LiteralElement, sm.Item.Element] = {
    "OTHER": sm.Item.Element.other,
    "PHYSICAL": sm.Item.Element.physical,
    "EXPLOSIVE": sm.Item.Element.explosive,
    "ELECTRIC": sm.Item.Element.electric,
    "COMBINED": sm.Item.Element.combined,
}
LITERAL_TIER_TO_ENUM: abc.Mapping[LiteralTier, sm.Item.Rarity] = {
    "COMMON": sm.Item.Rarity.common,
    "RARE": sm.Item.Rarity.rare,
    "EPIC": sm.Item.Rarity.epic,
    "LEGENDARY": sm.Item.Rarity.legendary,
    "MYTHICAL": sm.Item.Rarity.mythical,
    "DIVINE": sm.Item.Rarity.divine,
    "PERK": sm.Item.Rarity.perk,
}
LETTER_TO_TIER: abc.Mapping[str, sm.Item.Rarity] = {
    "c": sm.Item.Rarity.common,
    "r": sm.Item.Rarity.rare,
    "e": sm.Item.Rarity.epic,
    "l": sm.Item.Rarity.legendary,
    "m": sm.Item.Rarity.mythical,
    "d": sm.Item.Rarity.divine,
    "p": sm.Item.Rarity.perk,
}
TIER_TO_MAX_LEVEL: abc.Mapping[sm.Item.Rarity, int] = {
    sm.Item.Rarity.common: 10,
    sm.Item.Rarity.rare: 20,
    sm.Item.Rarity.epic: 30,
    sm.Item.Rarity.legendary: 40,
    sm.Item.Rarity.mythical: 50,
    sm.Item.Rarity.divine: 1,
    sm.Item.Rarity.perk: 1,
}


def convert_stats(stats: ItemStatsDto, /) -> sm.ItemStats:
    return sm.ItemStats(
        weight=stats.weight,
        hit_points=stats.hit_points,
        energy_capacity=stats.energy_capacity,
        energy_regeneration=stats.energy_regeneration,
        heat_capacity=stats.heat_capacity,
        heat_cooling=stats.heat_cooling,
        physical_resistance=stats.physical_resistance,
        explosive_resistance=stats.explosive_resistance,
        electric_resistance=stats.electric_resistance,
        bullets_capacity=stats.bullets_capacity,
        rockets_capacity=stats.rockets_capacity,
        walk=stats.walk,
        jump=stats.jump,
        physical_damage=stats.physical_damage[0],
        physical_damage_addon=stats.physical_damage[1],
        physical_resistance_damage=stats.physical_resistance_damage,
        electric_damage=stats.electric_damage[0],
        electric_damage_addon=stats.electric_damage[1],
        energy_damage=stats.energy_damage,
        energy_capacity_damage=stats.energy_capacity_damage,
        regeneration_damage=stats.energy_regeneration_damage,
        electric_resistance_damage=stats.electric_resistance_damage,
        explosive_damage=stats.explosive_damage[0],
        explosive_damage_addon=stats.explosive_damage[1],
        heat_damage=stats.heat_damage,
        heat_capacity_damage=stats.heat_capacity_damage,
        cooling_damage=stats.heat_cooling_damage,
        explosive_resistance_damage=stats.explosive_resistance_damage,
        range=stats.range[0],
        range_addon=stats.range[1],
        push=stats.push,
        pull=stats.pull,
        recoil=stats.recoil,
        advance=stats.advance,
        retreat=stats.retreat,
        uses=stats.uses,
        backfire=stats.backfire,
        repair=stats.repair,
        heat_generation=stats.heat_generation,
        energy_cost=stats.energy_cost,
        bullets_cost=stats.bullets_cost,
        rockets_cost=stats.rockets_cost,
    )


def get_unset_fields(fields: abc.Mapping[str, object | msgspec.UnsetType], /) -> list[str]:
    return [field for field, value in fields.items() if value is msgspec.UNSET]


def get_set_fields(fields: abc.Mapping[str, object | msgspec.UnsetType], /) -> list[str]:
    return [field for field, value in fields.items() if value is not msgspec.UNSET]


def unset_to_option[T](v: T | msgspec.UnsetType, /) -> Option[T]:
    return Null.null if v is msgspec.UNSET else Some(v)
