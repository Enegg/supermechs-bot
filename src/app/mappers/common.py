from collections import abc

import msgspec

from app.dto.common import ItemStatsDto, LiteralElement, LiteralSlot, LiteralSubtype, LiteralTier

import dupermechs.all as sm

type ItemMapping = abc.Mapping[sm.Item.Id, sm.Item]

LITERAL_SLOT_TO_ENUM: abc.Mapping[LiteralSlot, sm.Item.Slot] = {
    "TORSO": sm.Item.Slot.torso,
    "LEGS": sm.Item.Slot.legs,
    "DRONE": sm.Item.Slot.drone,
    "SIDE_WEAPON": sm.Item.Slot.side_weapon,
    "TOP_WEAPON": sm.Item.Slot.top_weapon,
    "CHARGE_ENGINE": sm.Item.Slot.charge,
    "CHARGE": sm.Item.Slot.charge,
    "TELEPORTER": sm.Item.Slot.teleport,
    "GRAPPLING_HOOK": sm.Item.Slot.hook,
    "HOOK": sm.Item.Slot.hook,
    "SHIELD": sm.Item.Slot.shield,
    "MODULE": sm.Item.Slot.module,
    "PERK": sm.Item.Slot.perk,
    "KIT": sm.Item.Slot.kit,
}
LITERAL_ELEMENT_TO_ENUM: abc.Mapping[LiteralElement, sm.Item.Element] = {
    "OTHER": sm.Item.Element.other,
    "PHYSICAL": sm.Item.Element.physical,
    "EXPLOSIVE": sm.Item.Element.explosive,
    "ELECTRIC": sm.Item.Element.electric,
    "COMBINED": sm.Item.Element.combined,
}
LITERAL_SUBTYPE_TO_ENUM: abc.Mapping[LiteralSubtype | msgspec.UnsetType, sm.Item.Subtype] = {
    "POWER_KIT": sm.Item.Subtype.power_kit,
    "COLOR_KIT": sm.Item.Subtype.color_kit,
    "TRANSFORM_RELIC": sm.Item.Subtype.transform_relic,
    "ASCENSION_RELIC": sm.Item.Subtype.ascension_relic,
    "TORSO_PERK": sm.Item.Subtype.torso_perk,
    "GIANT_PERK": sm.Item.Subtype.giant_perk,
    "TINY_PERK": sm.Item.Subtype.tiny_perk,
    "HAT_PERK": sm.Item.Subtype.hat_perk,
    "SHOTS_PERK": sm.Item.Subtype.shot_perk,
    "MELEE_WEAPON": sm.Item.Subtype.none,
    msgspec.UNSET: sm.Item.Subtype.none,
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
        physical_damage_min=stats.physical_damage[0],
        physical_damage_max=stats.physical_damage[1],
        physical_resistance_damage=stats.physical_resistance_damage,
        electric_damage_min=stats.electric_damage[0],
        electric_damage_max=stats.electric_damage[1],
        energy_damage=stats.energy_damage,
        energy_capacity_damage=stats.energy_capacity_damage,
        regeneration_damage=stats.energy_regeneration_damage,
        electric_resistance_damage=stats.electric_resistance_damage,
        explosive_damage_min=stats.explosive_damage[0],
        explosive_damage_max=stats.explosive_damage[1],
        heat_damage=stats.heat_damage,
        heat_capacity_damage=stats.heat_capacity_damage,
        cooling_damage=stats.heat_cooling_damage,
        explosive_resistance_damage=stats.explosive_resistance_damage,
        range_min=stats.range[0],
        range_max=stats.range[1],
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
        hit_points_per_block=stats.hp_per_block,
        heat_per_block=stats.heat_per_block,
        energy_per_block=stats.energy_per_block,
        block_percent_points=stats.absorb_ratio,
    )


def get_unset_fields(fields: abc.Mapping[str, object | msgspec.UnsetType], /) -> list[str]:
    return [field for field, value in fields.items() if value is msgspec.UNSET]


def get_set_fields(fields: abc.Mapping[str, object | msgspec.UnsetType], /) -> list[str]:
    return [field for field, value in fields.items() if value is not msgspec.UNSET]
