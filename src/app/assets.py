"""Various assets existing on discord side."""

import logging
from collections import abc
from typing import ClassVar, Final

import attrs

from disnake import Color

from app import paths
from app.class_utils import MappingParser
from resources import AnyResource, FileResource

import dupermechs.all as sm

__all__ = ("ASSETS", "COLORS", "EMOJIS", "ICONS")

_LOG = logging.getLogger(__name__)
NULL_EMOJI: Final[str] = "❔"
NULL_COLOR: Final[Color] = Color(0)
MISSING_IMAGE: Final[FileResource] = FileResource(paths.MISSING_PNG)


@attrs.frozen
class TypeEmojis:
    torso: str = NULL_EMOJI
    legs: str = NULL_EMOJI
    drone: str = NULL_EMOJI
    side_weapon: str = NULL_EMOJI
    right_side_weapon: str = NULL_EMOJI
    left_side_weapon: str = NULL_EMOJI
    top_weapon: str = NULL_EMOJI
    right_top_weapon: str = NULL_EMOJI
    left_top_weapon: str = NULL_EMOJI
    charge: str = NULL_EMOJI
    teleport: str = NULL_EMOJI
    hook: str = NULL_EMOJI
    shield: str = NULL_EMOJI
    module: str = NULL_EMOJI
    perk: str = NULL_EMOJI
    kit: str = NULL_EMOJI

    def __getitem__(self, field: sm.Item.Type, /) -> str:
        return getattr(self, field.name)


@attrs.frozen
class ElementEmojis:
    other: str = NULL_EMOJI
    physical: str = NULL_EMOJI
    explosive: str = NULL_EMOJI
    electric: str = NULL_EMOJI
    combined: str = NULL_EMOJI

    def __getitem__(self, field: sm.Item.Element, /) -> str:
        return getattr(self, field.name)


@attrs.frozen
class TierEmojis:
    common: str = NULL_EMOJI
    rare: str = NULL_EMOJI
    epic: str = NULL_EMOJI
    legendary: str = NULL_EMOJI
    mythical: str = NULL_EMOJI
    divine: str = NULL_EMOJI
    perk: str = NULL_EMOJI
    common_hollow: str = NULL_EMOJI
    rare_hollow: str = NULL_EMOJI
    epic_hollow: str = NULL_EMOJI
    legendary_hollow: str = NULL_EMOJI
    mythical_hollow: str = NULL_EMOJI
    divine_hollow: str = NULL_EMOJI
    perk_hollow: str = NULL_EMOJI

    def __getitem__(self, field: sm.Item.Rarity, /) -> str:
        return getattr(self, field.name)

    def get_hollow(self, field: sm.Item.Rarity, /) -> str:
        return getattr(self, f"{field.name}_hollow")


@attrs.frozen
class CardEmojis:
    common: str = NULL_EMOJI
    rare: str = NULL_EMOJI
    epic: str = NULL_EMOJI
    legendary: str = NULL_EMOJI
    mythical: str = NULL_EMOJI

    def __getitem__(self, field: sm.Item.Rarity, /) -> str | None:
        if field in (sm.Item.Rarity.divine, sm.Item.Rarity.perk):
            return None
        return getattr(self, field.name)


@attrs.frozen
class PowerKitEmojis:
    common: str = NULL_EMOJI
    rare: str = NULL_EMOJI


@attrs.frozen
class StatEmojis:
    weight: str = NULL_EMOJI
    hit_points: str = NULL_EMOJI
    energy_capacity: str = NULL_EMOJI
    energy_regeneration: str = NULL_EMOJI
    heat_capacity: str = NULL_EMOJI
    heat_cooling: str = NULL_EMOJI
    physical_resistance: str = NULL_EMOJI
    explosive_resistance: str = NULL_EMOJI
    electric_resistance: str = NULL_EMOJI
    bullets_capacity: str = NULL_EMOJI
    rockets_capacity: str = NULL_EMOJI
    walk: str = NULL_EMOJI
    jump: str = NULL_EMOJI
    physical_damage: str = NULL_EMOJI
    physical_damage_addon: str = NULL_EMOJI
    physical_resistance_damage: str = NULL_EMOJI
    electric_damage: str = NULL_EMOJI
    electric_damage_addon: str = NULL_EMOJI
    energy_damage: str = NULL_EMOJI
    energy_capacity_damage: str = NULL_EMOJI
    regeneration_damage: str = NULL_EMOJI
    electric_resistance_damage: str = NULL_EMOJI
    explosive_damage: str = NULL_EMOJI
    explosive_damage_addon: str = NULL_EMOJI
    heat_damage: str = NULL_EMOJI
    heat_capacity_damage: str = NULL_EMOJI
    cooling_damage: str = NULL_EMOJI
    explosive_resistance_damage: str = NULL_EMOJI
    range: str = NULL_EMOJI
    range_addon: str = NULL_EMOJI
    push: str = NULL_EMOJI
    pull: str = NULL_EMOJI
    recoil: str = NULL_EMOJI
    advance: str = NULL_EMOJI
    retreat: str = NULL_EMOJI
    uses: str = NULL_EMOJI
    backfire: str = NULL_EMOJI
    repair: str = NULL_EMOJI
    heat_generation: str = NULL_EMOJI
    energy_cost: str = NULL_EMOJI
    bullets_cost: str = NULL_EMOJI
    rockets_cost: str = NULL_EMOJI

    def __getitem__(self, field: sm.enums.ItemStat, /) -> str:
        return getattr(self, field.name)


@attrs.frozen
class CategoryEmojis:
    energy_capacity: str = NULL_EMOJI
    energy_regeneration: str = NULL_EMOJI
    energy_damage: str = NULL_EMOJI
    heat_capacity: str = NULL_EMOJI
    heat_cooling: str = NULL_EMOJI
    heat_damage: str = NULL_EMOJI
    physical_damage: str = NULL_EMOJI
    explosive_damage: str = NULL_EMOJI
    electric_damage: str = NULL_EMOJI
    physical_resistance: str = NULL_EMOJI
    explosive_resistance: str = NULL_EMOJI
    electric_resistance: str = NULL_EMOJI
    total_hp: str = NULL_EMOJI
    backfire_reduction: str = NULL_EMOJI
    damage_vs_titans: str = NULL_EMOJI

    def __getitem__(self, field: sm.enums.ArenaShopCategory, /) -> str:
        return getattr(self, field.name)


@attrs.frozen
class Emojis:
    types: TypeEmojis = attrs.Factory(TypeEmojis)
    tiers: TierEmojis = attrs.Factory(TierEmojis)
    elements: ElementEmojis = attrs.Factory(ElementEmojis)
    cards: CardEmojis = attrs.Factory(CardEmojis)
    power_kits: PowerKitEmojis = attrs.Factory(PowerKitEmojis)
    stats: StatEmojis = attrs.Factory(StatEmojis)
    categories: CategoryEmojis = attrs.Factory(CategoryEmojis)


@attrs.frozen
class TypeIcons:
    torso: AnyResource | None = None
    legs: AnyResource | None = None
    drone: AnyResource | None = None
    side_weapon: AnyResource | None = None
    right_side_weapon: AnyResource | None = None
    left_side_weapon: AnyResource | None = None
    top_weapon: AnyResource | None = None
    right_top_weapon: AnyResource | None = None
    left_top_weapon: AnyResource | None = None
    charge: AnyResource | None = None
    teleport: AnyResource | None = None
    hook: AnyResource | None = None
    shield: AnyResource | None = None
    module: AnyResource | None = None
    perk: AnyResource | None = None
    kit: AnyResource | None = None

    def __getitem__(self, field: sm.Item.Type, /) -> AnyResource | None:
        return getattr(self, field.name)


@attrs.frozen
class Icons:
    types: TypeIcons = attrs.Factory(TypeIcons)


@attrs.frozen
class ElementColors:
    other: Color = NULL_COLOR
    physical: Color = NULL_COLOR
    explosive: Color = NULL_COLOR
    electric: Color = NULL_COLOR
    combined: Color = NULL_COLOR

    def __getitem__(self, field: sm.Item.Element, /) -> Color:
        return getattr(self, field.name)


@attrs.frozen
class Colors:
    elements: ElementColors = attrs.Factory(ElementColors)
    error: ClassVar = Color.from_hex("#FF0000")
    warning: ClassVar = Color.from_hex("#FFBB00")
    info: ClassVar = Color.from_hex("#0088FF")


@attrs.frozen
class Assets:
    frantic_gifs: abc.Sequence[str]


_PARSER = MappingParser.from_path(paths.ASSETS_TOML)
ASSETS = _PARSER.structure(Assets, "misc")
EMOJIS = _PARSER.structure(Emojis, "emojis")
ICONS = _PARSER.structure(Icons, "icons")
COLORS = _PARSER.structure(Colors, "colors")
del _PARSER


def get_slot_icon(type: sm.Item.Type, /) -> AnyResource | None:
    if type is sm.Item.Type.side_weapon:
        return ICONS.types.right_side_weapon

    if type is sm.Item.Type.top_weapon:
        return ICONS.types.right_top_weapon

    return ICONS.types[type]
