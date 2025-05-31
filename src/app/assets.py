"""Various assets existing on discord side."""

import logging
import math
from collections import abc
from typing import Final

import attrs

from disnake import Color

from app import paths
from app.class_utils import MappingParser
from app.gamerules import BUILD_RULES
from resources import AnyResource, FileResource

import dupermechs.all as sm
from dupermechs.enums import MechSlot

__all__ = ("ASSETS", "COLORS", "EMOJIS", "ICONS", "get_silhouette")

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

    def __getitem__(self, field: sm.Item.Rarity, /) -> str:
        return getattr(self, field.name)


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

    def __getitem__(self, field: sm.enums.ItemStat | sm.enums.MechStat, /) -> str:
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
    stats: StatEmojis = attrs.Factory(StatEmojis)
    categories: CategoryEmojis = attrs.Factory(CategoryEmojis)

    @staticmethod
    def get_weight_emoji(weight: int, /) -> str:
        if weight < 0:
            return "🎈"
        progress = math.floor(BUILD_RULES.safe_weight * 0.9)
        if weight < progress:
            emojis = ("", "▫️", "◽", "◻️", "🔲", "⬜")
            return emojis[round((len(emojis) - 1) * weight / progress)]
        if weight < math.floor(BUILD_RULES.safe_weight * 0.99):
            return "🟦"
        if weight < BUILD_RULES.safe_weight:
            return "🟩"
        if weight == BUILD_RULES.safe_weight:
            return "✅"
        if weight <= BUILD_RULES.max_weight:
            return "🟨"
        return "⛔"


def get_slot_emoji(slot: MechSlot, /) -> str:
    """Return the emoji representing a slot, with respect to the right & left variants."""
    if slot is MechSlot.top_weapon_1:
        return EMOJIS.types.left_top_weapon
    if slot is MechSlot.top_weapon_2:
        return EMOJIS.types.right_top_weapon
    if slot in (MechSlot.side_weapon_1, MechSlot.side_weapon_3):
        return EMOJIS.types.left_side_weapon
    if slot in (MechSlot.side_weapon_2, MechSlot.side_weapon_4):
        return EMOJIS.types.right_side_weapon
    if slot.name.startswith("module"):
        return EMOJIS.types.module
    # TODO: this is the only place using types[]
    return EMOJIS.types[sm.Item.Type[slot.name]]


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


@attrs.frozen
class Assets:
    frantic_gifs: abc.Sequence[str]


_PARSER = MappingParser.from_path(paths.ASSETS_TOML)
ASSETS = _PARSER.structure(Assets, "misc")
EMOJIS = _PARSER.structure(Emojis, "emojis")
ICONS = _PARSER.structure(Icons, "icons")
COLORS = _PARSER.structure(Colors, "colors")
del _PARSER


_SILHOUETTES: Final[abc.Mapping[sm.Item.Type, FileResource]] = {}


def _populate_silhouettes() -> None:
    for path in paths.SILHOUETTES_DIR.iterdir():
        try:
            type = sm.Item.Type[path.stem.lower()]

        except KeyError:
            _LOG.error("%s is not a valid silhouette", path)

        else:
            _SILHOUETTES[type] = FileResource(path)


_populate_silhouettes()
del _populate_silhouettes


def get_silhouette[T](type: sm.Item.Type, /, default: T = None) -> FileResource | T:
    return _SILHOUETTES.get(type, default)


def get_slot_icon(type: sm.Item.Type, /) -> AnyResource | None:
    if type is sm.Item.Type.side_weapon:
        return ICONS.types.right_side_weapon

    if type is sm.Item.Type.top_weapon:
        return ICONS.types.right_top_weapon

    return ICONS.types[type]
