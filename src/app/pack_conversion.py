import datetime as dt
from collections import abc
from typing import NamedTuple

import msgspec

from app import dto, structs
from app.structs import ItemMapping

import supermechs.all as sm

LITERAL_SLOT_TO_ENUM: abc.Mapping[dto.LiteralSlot, sm.Item.Slot] = {
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
LITERAL_ELEMENT_TO_ENUM: abc.Mapping[dto.LiteralElement, sm.Item.Element] = {
    "OTHER": sm.Item.Element.other,
    "PHYSICAL": sm.Item.Element.physical,
    "EXPLOSIVE": sm.Item.Element.explosive,
    "ELECTRIC": sm.Item.Element.electric,
    "COMBINED": sm.Item.Element.combined,
}
LITERAL_SUBTYPE_TO_ENUM: abc.Mapping[dto.LiteralSubtype | msgspec.UnsetType, sm.Item.Subtype] = {
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
LITERAL_TIER_TO_ENUM: abc.Mapping[dto.LiteralTier, sm.Item.Rarity] = {
    "COMMON": sm.Item.Rarity.common,
    "RARE": sm.Item.Rarity.rare,
    "EPIC": sm.Item.Rarity.epic,
    "LEGENDARY": sm.Item.Rarity.legendary,
    "MYTHICAL": sm.Item.Rarity.mythical,
    "DIVINE": sm.Item.Rarity.divine,
    "PERK": sm.Item.Rarity.perk,
}


type SpriteCollection = abc.Sequence[SpriteData]


class SpriteData(NamedTuple):
    item_id: sm.Item.Id
    image: str
    tier: sm.Item.Rarity
    reloaded: bool


def collect_items(
    item_dtos: abc.Sequence[dto.ItemDto], /
) -> tuple[structs.ItemPack, SpriteCollection]:
    reloaded_items: ItemMapping = {}
    legacy_items: ItemMapping = {}
    hidden_items: ItemMapping = {}
    all_images: SpriteCollection = []

    for item_dto in item_dtos:
        stages: list[sm.Item.Stage] = []
        id = sm.Item.Id(item_dto.id)

        for stage_dto in item_dto.stages:
            tier = LITERAL_TIER_TO_ENUM[stage_dto.tier]
            all_images.append(SpriteData(id, stage_dto.image, tier, item_dto.reloaded))

            levels = [
                sm.Item.Stage.Level(
                    level=level_dto.display_level,
                    power_required=level_dto.min_power_to_have,
                    power_contribution=level_dto.power_contribution,
                    stats=sm.ItemStats(
                        weight=(stats := level_dto.stats).weight,
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
                        block_percentage=stats.absorb_ratio,
                    ),
                    upgrade_gold_cost=level_dto.upgrade_gold_cost,
                )
                for level_dto in stage_dto.levels
            ]
            if not levels:
                levels.append(sm.Item.Stage.Level(level=1))

            stages.append(
                sm.Item.Stage(
                    tier=tier,
                    levels=tuple(levels),
                    evolution_gold_cost=stage_dto.evolution_gold_cost,
                    ascension_gold_cost=stage_dto.ascension_gold_cost,
                )
            )

        if not stages:
            stages.append(sm.Item.Stage(tier=sm.Item.Rarity.common, levels=[sm.Item.Stage.Level()]))

        item = sm.Item(
            id=id,
            name=item_dto.name,
            slot_id=LITERAL_SLOT_TO_ENUM[item_dto.slot_id],
            element=LITERAL_ELEMENT_TO_ENUM[item_dto.element],
            subtype=LITERAL_SUBTYPE_TO_ENUM[item_dto.subtype],
            stages=tuple(stages),
            release_date=(
                dt.datetime.fromtimestamp(item_dto.released_at, tz=dt.UTC)
                if item_dto.released_at
                else None
            ),
        )
        if item_dto.hidden:
            hidden_items[item.id] = item
        elif item_dto.reloaded:
            reloaded_items[item.id] = item
        else:
            legacy_items[item.id] = item

    pack = structs.ItemPack(
        reloaded_items=reloaded_items, legacy_items=legacy_items, hidden_items=hidden_items
    )
    return pack, all_images
