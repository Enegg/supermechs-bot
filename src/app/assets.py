"""Various assets existing on discord side."""

from collections import abc
from typing import Final, final

import attrs

from discord.emoji import AnyEmoji, UnicodeEmoji
from disnake import Color

from app import paths
from app.class_utils import MappingParser
from resources import AnyResource, FileResource, HttpResource

import supermechs.all as sm

__all__ = ("ASSETS", "COLORS", "EMOJIS", "ICONS")

NULL_EMOJI: Final = UnicodeEmoji("❔")
NULL_COLOR: Final = Color.default()
MISSING_IMAGE: Final = FileResource(paths.MISSING_PNG)


@final
class NoneEmoji:
    """Emoji that converts to None."""

    @staticmethod
    def to_partial() -> None:
        return None

    @staticmethod
    def to_asset() -> None:
        return None


@attrs.frozen
class Emojis:
    item_slot_torso: AnyEmoji = NULL_EMOJI
    item_slot_legs: AnyEmoji = NULL_EMOJI
    item_slot_drone: AnyEmoji = NULL_EMOJI
    item_slot_side_weapon: AnyEmoji = NULL_EMOJI
    mech_slot_right_side_weapon: AnyEmoji = NULL_EMOJI
    mech_slot_left_side_weapon: AnyEmoji = NULL_EMOJI
    item_slot_top_weapon: AnyEmoji = NULL_EMOJI
    mech_slot_right_top_weapon: AnyEmoji = NULL_EMOJI
    mech_slot_left_top_weapon: AnyEmoji = NULL_EMOJI
    item_slot_charge: AnyEmoji = NULL_EMOJI
    item_slot_teleport: AnyEmoji = NULL_EMOJI
    item_slot_hook: AnyEmoji = NULL_EMOJI
    item_slot_shield: AnyEmoji = NULL_EMOJI
    item_slot_module: AnyEmoji = NULL_EMOJI
    item_slot_perk: AnyEmoji = NULL_EMOJI
    item_slot_kit: AnyEmoji = NULL_EMOJI

    def get_item_slot(self, field: sm.Item.Slot, /) -> AnyEmoji:
        return getattr(self, "item_slot_" + field.name)

    element_other: AnyEmoji = NULL_EMOJI
    element_physical: AnyEmoji = NULL_EMOJI
    element_explosive: AnyEmoji = NULL_EMOJI
    element_electric: AnyEmoji = NULL_EMOJI
    element_combined: AnyEmoji = NULL_EMOJI

    def get_element(self, field: sm.Item.Element, /) -> AnyEmoji:
        return getattr(self, "element_" + field.name)

    tier_common: AnyEmoji = NULL_EMOJI
    tier_rare: AnyEmoji = NULL_EMOJI
    tier_epic: AnyEmoji = NULL_EMOJI
    tier_legendary: AnyEmoji = NULL_EMOJI
    tier_mythical: AnyEmoji = NULL_EMOJI
    tier_divine: AnyEmoji = NULL_EMOJI
    tier_perk: AnyEmoji = NULL_EMOJI
    tier_common_hollow: AnyEmoji = NULL_EMOJI
    tier_rare_hollow: AnyEmoji = NULL_EMOJI
    tier_epic_hollow: AnyEmoji = NULL_EMOJI
    tier_legendary_hollow: AnyEmoji = NULL_EMOJI
    tier_mythical_hollow: AnyEmoji = NULL_EMOJI
    tier_divine_hollow: AnyEmoji = NULL_EMOJI
    tier_perk_hollow: AnyEmoji = NULL_EMOJI

    def get_tier(self, field: sm.Item.Rarity, /, hollow: bool = False) -> AnyEmoji:
        if hollow:
            return getattr(self, f"tier_{field.name}_hollow")
        return getattr(self, "tier_" + field.name)

    card_common: AnyEmoji = NULL_EMOJI
    card_rare: AnyEmoji = NULL_EMOJI
    card_epic: AnyEmoji = NULL_EMOJI
    card_legendary: AnyEmoji = NULL_EMOJI
    card_mythical: AnyEmoji = NULL_EMOJI

    def get_card(self, field: sm.Item.Rarity, /) -> AnyEmoji | None:
        if field in (sm.Item.Rarity.divine, sm.Item.Rarity.perk):
            return None
        return getattr(self, "card_" + field.name)

    power_kit_common: AnyEmoji = NULL_EMOJI
    power_kit_rare: AnyEmoji = NULL_EMOJI

    stat_weight: AnyEmoji = NULL_EMOJI
    stat_hit_points: AnyEmoji = NULL_EMOJI
    stat_energy_capacity: AnyEmoji = NULL_EMOJI
    stat_energy_regeneration: AnyEmoji = NULL_EMOJI
    stat_heat_capacity: AnyEmoji = NULL_EMOJI
    stat_heat_cooling: AnyEmoji = NULL_EMOJI
    stat_physical_resistance: AnyEmoji = NULL_EMOJI
    stat_explosive_resistance: AnyEmoji = NULL_EMOJI
    stat_electric_resistance: AnyEmoji = NULL_EMOJI
    stat_bullets_capacity: AnyEmoji = NULL_EMOJI
    stat_rockets_capacity: AnyEmoji = NULL_EMOJI
    stat_walk: AnyEmoji = NULL_EMOJI
    stat_jump: AnyEmoji = NULL_EMOJI
    stat_physical_damage: AnyEmoji = NULL_EMOJI
    stat_physical_damage_addon: AnyEmoji = NULL_EMOJI
    stat_physical_resistance_damage: AnyEmoji = NULL_EMOJI
    stat_electric_damage: AnyEmoji = NULL_EMOJI
    stat_electric_damage_addon: AnyEmoji = NULL_EMOJI
    stat_energy_damage: AnyEmoji = NULL_EMOJI
    stat_energy_capacity_damage: AnyEmoji = NULL_EMOJI
    stat_regeneration_damage: AnyEmoji = NULL_EMOJI
    stat_electric_resistance_damage: AnyEmoji = NULL_EMOJI
    stat_explosive_damage: AnyEmoji = NULL_EMOJI
    stat_explosive_damage_addon: AnyEmoji = NULL_EMOJI
    stat_heat_damage: AnyEmoji = NULL_EMOJI
    stat_heat_capacity_damage: AnyEmoji = NULL_EMOJI
    stat_cooling_damage: AnyEmoji = NULL_EMOJI
    stat_explosive_resistance_damage: AnyEmoji = NULL_EMOJI
    stat_range: AnyEmoji = NULL_EMOJI
    stat_range_addon: AnyEmoji = NULL_EMOJI
    stat_push: AnyEmoji = NULL_EMOJI
    stat_pull: AnyEmoji = NULL_EMOJI
    stat_recoil: AnyEmoji = NULL_EMOJI
    stat_advance: AnyEmoji = NULL_EMOJI
    stat_retreat: AnyEmoji = NULL_EMOJI
    stat_uses: AnyEmoji = NULL_EMOJI
    stat_backfire: AnyEmoji = NULL_EMOJI
    stat_repair: AnyEmoji = NULL_EMOJI
    stat_heat_generation: AnyEmoji = NULL_EMOJI
    stat_energy_cost: AnyEmoji = NULL_EMOJI
    stat_bullets_cost: AnyEmoji = NULL_EMOJI
    stat_rockets_cost: AnyEmoji = NULL_EMOJI
    stat_shield_absorption: AnyEmoji = NULL_EMOJI

    def get_stat(self, field: sm.enums.ItemStat, /) -> AnyEmoji:
        return getattr(self, "stat_" + field.name)

    buff_energy_capacity: AnyEmoji = NULL_EMOJI
    buff_energy_regeneration: AnyEmoji = NULL_EMOJI
    buff_energy_damage: AnyEmoji = NULL_EMOJI
    buff_heat_capacity: AnyEmoji = NULL_EMOJI
    buff_heat_cooling: AnyEmoji = NULL_EMOJI
    buff_heat_damage: AnyEmoji = NULL_EMOJI
    buff_physical_damage: AnyEmoji = NULL_EMOJI
    buff_explosive_damage: AnyEmoji = NULL_EMOJI
    buff_electric_damage: AnyEmoji = NULL_EMOJI
    buff_physical_resistance: AnyEmoji = NULL_EMOJI
    buff_explosive_resistance: AnyEmoji = NULL_EMOJI
    buff_electric_resistance: AnyEmoji = NULL_EMOJI
    buff_total_hp: AnyEmoji = NULL_EMOJI
    buff_backfire_reduction: AnyEmoji = NULL_EMOJI
    buff_damage_vs_titans: AnyEmoji = NULL_EMOJI

    def get_buff(self, field: sm.enums.ArenaShopCategory, /) -> AnyEmoji:
        return getattr(self, "buff_" + field.name)

    ranks: abc.Sequence[AnyEmoji] = ()

    def get_rank[T](self, rank: int, /, default: T = NULL_EMOJI) -> AnyEmoji | T:
        if rank < len(self.ranks):
            return self.ranks[rank]
        return default


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
        icon: AnyResource | None = getattr(self, "item_slot_" + field.name)

        if icon is not None:
            return icon

        emoji = EMOJIS.get_item_slot(field)

        if asset := emoji.to_asset():
            return HttpResource.from_uri(asset.full_url)

        return None


class Colors:
    __slots__ = ()

    tier_common: Final = Color.from_hex("#B1B1B1")
    tier_rare: Final = Color.from_hex("#55ACEE")
    tier_epic: Final = Color.from_hex("#CC41CC")
    tier_legendary: Final = Color.from_hex("#E0A23C")
    tier_mythical: Final = Color.from_hex("#FE6333")
    tier_divine: Final = Color.from_hex("#FFFFFF")
    tier_perk: Final = Color.from_hex("#FFFF33")

    @classmethod
    def get_tier(cls, field: sm.Item.Rarity, /) -> Color:
        return getattr(cls, "tier_" + field.name)

    element_other: Final = Color.from_hex("#323232")
    element_physical: Final = Color.from_hex("#FFB800")
    element_explosive: Final = Color.from_hex("#B71010")
    element_electric: Final = Color.from_hex("#106ED8")
    element_combined: Final = Color.from_hex("#211D1D")

    @classmethod
    def get_element(cls, field: sm.Item.Element, /) -> Color:
        return getattr(cls, "element_" + field.name)

    error: Final = Color.from_hex("#FF0000")
    warning: Final = Color.from_hex("#FFBB00")
    info: Final = Color.from_hex("#0088FF")


@attrs.frozen
class Assets:
    frantic_gifs: abc.Sequence[str]


_PARSER = MappingParser.from_path(paths.ASSETS_TOML)
ASSETS = _PARSER.structure(Assets, "misc")
EMOJIS = _PARSER.structure(Emojis, "emojis")
ICONS = _PARSER.structure(Icons, "icon_overrides")
COLORS = Colors()
del _PARSER
