"""Various assets existing on discord side."""

from collections import abc
from typing import Final

import attrs

from disnake import Color

from app import paths
from app.class_utils import MappingParser
from resources import AnyResource, FileResource

import dupermechs.all as sm

__all__ = ("ASSETS", "COLORS", "EMOJIS", "ICONS")

NULL_EMOJI: Final[str] = "❔"
NULL_COLOR: Final[Color] = Color(0)
MISSING_IMAGE: Final[FileResource] = FileResource(paths.MISSING_PNG)


@attrs.frozen
class Emojis:
    item_slot_torso: str = NULL_EMOJI
    item_slot_legs: str = NULL_EMOJI
    item_slot_drone: str = NULL_EMOJI
    item_slot_side_weapon: str = NULL_EMOJI
    mech_slot_right_side_weapon: str = NULL_EMOJI
    mech_slot_left_side_weapon: str = NULL_EMOJI
    item_slot_top_weapon: str = NULL_EMOJI
    mech_slot_right_top_weapon: str = NULL_EMOJI
    mech_slot_left_top_weapon: str = NULL_EMOJI
    item_slot_charge: str = NULL_EMOJI
    item_slot_teleport: str = NULL_EMOJI
    item_slot_hook: str = NULL_EMOJI
    item_slot_shield: str = NULL_EMOJI
    item_slot_module: str = NULL_EMOJI
    item_slot_perk: str = NULL_EMOJI
    item_slot_kit: str = NULL_EMOJI

    def get_item_slot(self, field: sm.Item.Slot, /) -> str:
        return getattr(self, "item_slot_" + field.name)

    element_other: str = NULL_EMOJI
    element_physical: str = NULL_EMOJI
    element_explosive: str = NULL_EMOJI
    element_electric: str = NULL_EMOJI
    element_combined: str = NULL_EMOJI

    def get_element(self, field: sm.Item.Element, /) -> str:
        return getattr(self, "element_" + field.name)

    tier_common: str = NULL_EMOJI
    tier_rare: str = NULL_EMOJI
    tier_epic: str = NULL_EMOJI
    tier_legendary: str = NULL_EMOJI
    tier_mythical: str = NULL_EMOJI
    tier_divine: str = NULL_EMOJI
    tier_perk: str = NULL_EMOJI
    tier_common_hollow: str = NULL_EMOJI
    tier_rare_hollow: str = NULL_EMOJI
    tier_epic_hollow: str = NULL_EMOJI
    tier_legendary_hollow: str = NULL_EMOJI
    tier_mythical_hollow: str = NULL_EMOJI
    tier_divine_hollow: str = NULL_EMOJI
    tier_perk_hollow: str = NULL_EMOJI

    def get_tier(self, field: sm.Item.Rarity, /, hollow: bool = False) -> str:
        if hollow:
            return getattr(self, f"tier_{field.name}_hollow")
        return getattr(self, "tier_" + field.name)

    card_common: str = NULL_EMOJI
    card_rare: str = NULL_EMOJI
    card_epic: str = NULL_EMOJI
    card_legendary: str = NULL_EMOJI
    card_mythical: str = NULL_EMOJI

    def get_card(self, field: sm.Item.Rarity, /) -> str | None:
        if field in (sm.Item.Rarity.divine, sm.Item.Rarity.perk):
            return None
        return getattr(self, "card_" + field.name)

    power_kit_common: str = NULL_EMOJI
    power_kit_rare: str = NULL_EMOJI

    stat_weight: str = NULL_EMOJI
    stat_hit_points: str = NULL_EMOJI
    stat_energy_capacity: str = NULL_EMOJI
    stat_energy_regeneration: str = NULL_EMOJI
    stat_heat_capacity: str = NULL_EMOJI
    stat_heat_cooling: str = NULL_EMOJI
    stat_physical_resistance: str = NULL_EMOJI
    stat_explosive_resistance: str = NULL_EMOJI
    stat_electric_resistance: str = NULL_EMOJI
    stat_bullets_capacity: str = NULL_EMOJI
    stat_rockets_capacity: str = NULL_EMOJI
    stat_walk: str = NULL_EMOJI
    stat_jump: str = NULL_EMOJI
    stat_physical_damage: str = NULL_EMOJI
    stat_physical_damage_addon: str = NULL_EMOJI
    stat_physical_resistance_damage: str = NULL_EMOJI
    stat_electric_damage: str = NULL_EMOJI
    stat_electric_damage_addon: str = NULL_EMOJI
    stat_energy_damage: str = NULL_EMOJI
    stat_energy_capacity_damage: str = NULL_EMOJI
    stat_regeneration_damage: str = NULL_EMOJI
    stat_electric_resistance_damage: str = NULL_EMOJI
    stat_explosive_damage: str = NULL_EMOJI
    stat_explosive_damage_addon: str = NULL_EMOJI
    stat_heat_damage: str = NULL_EMOJI
    stat_heat_capacity_damage: str = NULL_EMOJI
    stat_cooling_damage: str = NULL_EMOJI
    stat_explosive_resistance_damage: str = NULL_EMOJI
    stat_range: str = NULL_EMOJI
    stat_range_addon: str = NULL_EMOJI
    stat_push: str = NULL_EMOJI
    stat_pull: str = NULL_EMOJI
    stat_recoil: str = NULL_EMOJI
    stat_advance: str = NULL_EMOJI
    stat_retreat: str = NULL_EMOJI
    stat_uses: str = NULL_EMOJI
    stat_backfire: str = NULL_EMOJI
    stat_repair: str = NULL_EMOJI
    stat_heat_generation: str = NULL_EMOJI
    stat_energy_cost: str = NULL_EMOJI
    stat_bullets_cost: str = NULL_EMOJI
    stat_rockets_cost: str = NULL_EMOJI
    stat_shield_absorption: str = NULL_EMOJI

    def get_stat(self, field: sm.enums.ItemStat, /) -> str:
        return getattr(self, "stat_" + field.name)

    buff_energy_capacity: str = NULL_EMOJI
    buff_energy_regeneration: str = NULL_EMOJI
    buff_energy_damage: str = NULL_EMOJI
    buff_heat_capacity: str = NULL_EMOJI
    buff_heat_cooling: str = NULL_EMOJI
    buff_heat_damage: str = NULL_EMOJI
    buff_physical_damage: str = NULL_EMOJI
    buff_explosive_damage: str = NULL_EMOJI
    buff_electric_damage: str = NULL_EMOJI
    buff_physical_resistance: str = NULL_EMOJI
    buff_explosive_resistance: str = NULL_EMOJI
    buff_electric_resistance: str = NULL_EMOJI
    buff_total_hp: str = NULL_EMOJI
    buff_backfire_reduction: str = NULL_EMOJI
    buff_damage_vs_titans: str = NULL_EMOJI

    def get_buff(self, field: sm.enums.ArenaShopCategory, /) -> str:
        return getattr(self, "buff_" + field.name)


@attrs.frozen
class Icons:
    item_slot_torso: AnyResource | None = None
    item_slot_legs: AnyResource | None = None
    item_slot_drone: AnyResource | None = None
    item_slot_side_weapon: AnyResource | None = None
    mech_slot_right_side_weapon: AnyResource | None = None
    mech_slot_left_side_weapon: AnyResource | None = None
    item_slot_top_weapon: AnyResource | None = None
    mech_slot_right_top_weapon: AnyResource | None = None
    mech_slot_left_top_weapon: AnyResource | None = None
    item_slot_charge: AnyResource | None = None
    item_slot_teleport: AnyResource | None = None
    item_slot_hook: AnyResource | None = None
    item_slot_shield: AnyResource | None = None
    item_slot_module: AnyResource | None = None
    item_slot_perk: AnyResource | None = None
    item_slot_kit: AnyResource | None = None

    def get_item_slot(self, field: sm.Item.Slot, /) -> AnyResource | None:
        return getattr(self, "item_slot_" + field.name)


class Colors:
    __slots__ = ()

    tier_common: Final[Color] = Color.from_hex("#B1B1B1")
    tier_rare: Final[Color] = Color.from_hex("#55ACEE")
    tier_epic: Final[Color] = Color.from_hex("#CC41CC")
    tier_legendary: Final[Color] = Color.from_hex("#E0A23C")
    tier_mythical: Final[Color] = Color.from_hex("#FE6333")
    tier_divine: Final[Color] = Color.from_hex("#FFFFFF")
    tier_perk: Final[Color] = Color.from_hex("#FFFF33")

    @classmethod
    def get_tier(cls, field: sm.Item.Rarity, /) -> Color:
        return getattr(cls, "tier_" + field.name)

    element_other: Final[Color] = Color.from_hex("#323232")
    element_physical: Final[Color] = Color.from_hex("#FFB800")
    element_explosive: Final[Color] = Color.from_hex("#B71010")
    element_electric: Final[Color] = Color.from_hex("#106ED8")
    element_combined: Final[Color] = Color.from_hex("#211D1D")

    @classmethod
    def get_element(cls, field: sm.Item.Element, /) -> Color:
        return getattr(cls, "element_" + field.name)

    error: Final[Color] = Color.from_hex("#FF0000")
    warning: Final[Color] = Color.from_hex("#FFBB00")
    info: Final[Color] = Color.from_hex("#0088FF")


@attrs.frozen
class Assets:
    frantic_gifs: abc.Sequence[str]


_PARSER = MappingParser.from_path(paths.ASSETS_TOML)
ASSETS = _PARSER.structure(Assets, "misc")
EMOJIS = _PARSER.structure(Emojis, "emojis")
ICONS = _PARSER.structure(Icons, "icons")
COLORS = Colors()
del _PARSER
