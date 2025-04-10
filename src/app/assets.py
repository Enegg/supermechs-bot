"""Various assets existing on discord side."""

import math
from collections import abc

import attrs
import cattrs

from disnake import Color

from app import paths
from app.class_utils import MappingParser
from app.core import CONFIG
from resources import Resource

import supermechs.all as sm
from supermechs.gamerules import BuildRules

__all__ = ("ASSETS", "COLORS", "EMOJIS", "ICONS")

_DEFAULT_EMOJI = "❔"
_DEFAULT_RESOURCE = Resource.from_uri(CONFIG.missing_image_url)
_DEFAULT_COLOR = Color(0)


@cattrs.global_converter.register_structure_hook
def _structure_color(value: int, cls: type) -> Color:
    return Color(int(value))


@cattrs.global_converter.register_structure_hook
def _structure_resource(value: str, cls: type) -> Resource:
    assert isinstance(value, str)
    return Resource.from_uri(value)


del _structure_color, _structure_resource


@attrs.frozen
class TypeEmojis:
    none: str = _DEFAULT_EMOJI
    torso: str = _DEFAULT_EMOJI
    legs: str = _DEFAULT_EMOJI
    drone: str = _DEFAULT_EMOJI
    side_weapon: str = _DEFAULT_EMOJI
    right_side_weapon: str = _DEFAULT_EMOJI
    left_side_weapon: str = _DEFAULT_EMOJI
    top_weapon: str = _DEFAULT_EMOJI
    right_top_weapon: str = _DEFAULT_EMOJI
    left_top_weapon: str = _DEFAULT_EMOJI
    charge: str = _DEFAULT_EMOJI
    teleport: str = _DEFAULT_EMOJI
    hook: str = _DEFAULT_EMOJI
    shield: str = _DEFAULT_EMOJI
    module: str = _DEFAULT_EMOJI
    perk: str = _DEFAULT_EMOJI
    kit: str = _DEFAULT_EMOJI

    def __getitem__(self, field: sm.abc.ItemType) -> str:
        return getattr(self, field)


@attrs.frozen
class ElementEmojis:
    none: str = _DEFAULT_EMOJI
    physical: str = _DEFAULT_EMOJI
    explosive: str = _DEFAULT_EMOJI
    electric: str = _DEFAULT_EMOJI
    combined: str = _DEFAULT_EMOJI

    def __getitem__(self, field: sm.abc.ItemElement) -> str:
        return getattr(self, field)


@attrs.frozen
class TierEmojis:
    none: str = _DEFAULT_EMOJI
    common: str = _DEFAULT_EMOJI
    rare: str = _DEFAULT_EMOJI
    epic: str = _DEFAULT_EMOJI
    legendary: str = _DEFAULT_EMOJI
    mythical: str = _DEFAULT_EMOJI
    divine: str = _DEFAULT_EMOJI
    perk: str = _DEFAULT_EMOJI

    def __getitem__(self, field: sm.abc.StageTier) -> str:
        return getattr(self, field)


@attrs.frozen
class StatEmojis:
    unknown: str = _DEFAULT_EMOJI
    weight: str = _DEFAULT_EMOJI
    hit_points: str = _DEFAULT_EMOJI
    energy_capacity: str = _DEFAULT_EMOJI
    energy_regeneration: str = _DEFAULT_EMOJI
    heat_capacity: str = _DEFAULT_EMOJI
    heat_cooling: str = _DEFAULT_EMOJI
    physical_resistance: str = _DEFAULT_EMOJI
    explosive_resistance: str = _DEFAULT_EMOJI
    electric_resistance: str = _DEFAULT_EMOJI
    bullets_capacity: str = _DEFAULT_EMOJI
    rockets_capacity: str = _DEFAULT_EMOJI
    walk: str = _DEFAULT_EMOJI
    jump: str = _DEFAULT_EMOJI
    physical_damage: str = _DEFAULT_EMOJI
    physical_damage_addon: str = _DEFAULT_EMOJI
    physical_resistance_damage: str = _DEFAULT_EMOJI
    electric_damage: str = _DEFAULT_EMOJI
    electric_damage_addon: str = _DEFAULT_EMOJI
    energy_damage: str = _DEFAULT_EMOJI
    energy_capacity_damage: str = _DEFAULT_EMOJI
    regeneration_damage: str = _DEFAULT_EMOJI
    electric_resistance_damage: str = _DEFAULT_EMOJI
    explosive_damage: str = _DEFAULT_EMOJI
    explosive_damage_addon: str = _DEFAULT_EMOJI
    heat_damage: str = _DEFAULT_EMOJI
    heat_capacity_damage: str = _DEFAULT_EMOJI
    cooling_damage: str = _DEFAULT_EMOJI
    explosive_resistance_damage: str = _DEFAULT_EMOJI
    range: str = _DEFAULT_EMOJI
    range_addon: str = _DEFAULT_EMOJI
    push: str = _DEFAULT_EMOJI
    pull: str = _DEFAULT_EMOJI
    recoil: str = _DEFAULT_EMOJI
    advance: str = _DEFAULT_EMOJI
    retreat: str = _DEFAULT_EMOJI
    uses: str = _DEFAULT_EMOJI
    backfire: str = _DEFAULT_EMOJI
    heat_generation: str = _DEFAULT_EMOJI
    energy_cost: str = _DEFAULT_EMOJI
    bullets_cost: str = _DEFAULT_EMOJI
    rockets_cost: str = _DEFAULT_EMOJI

    def __getitem__(self, field: str) -> str:
        return getattr(self, field)


@attrs.frozen
class CategoryEmojis:
    energy_capacity: str = _DEFAULT_EMOJI
    energy_regeneration: str = _DEFAULT_EMOJI
    energy_damage: str = _DEFAULT_EMOJI
    heat_capacity: str = _DEFAULT_EMOJI
    heat_cooling: str = _DEFAULT_EMOJI
    heat_damage: str = _DEFAULT_EMOJI
    physical_damage: str = _DEFAULT_EMOJI
    explosive_damage: str = _DEFAULT_EMOJI
    electric_damage: str = _DEFAULT_EMOJI
    physical_resistance: str = _DEFAULT_EMOJI
    explosive_resistance: str = _DEFAULT_EMOJI
    electric_resistance: str = _DEFAULT_EMOJI
    total_hp: str = _DEFAULT_EMOJI
    backfire_reduction: str = _DEFAULT_EMOJI
    damage_vs_titans: str = _DEFAULT_EMOJI

    def __getitem__(self, field: str) -> str:
        return getattr(self, field)


@attrs.frozen
class Emojis:
    types: TypeEmojis = attrs.Factory(TypeEmojis)
    tiers: TierEmojis = attrs.Factory(TierEmojis)
    elements: ElementEmojis = attrs.Factory(ElementEmojis)
    stats: StatEmojis = attrs.Factory(StatEmojis)
    categories: CategoryEmojis = attrs.Factory(CategoryEmojis)

    @staticmethod
    def get_weight_emoji(weight: int, /, *, rules: BuildRules = CONFIG.build_rules) -> str:
        if weight < 0:
            return "🎈"
        progress = math.floor(rules.safe_weight * 0.9)
        if weight < progress:
            emojis = ("", "▫️", "◽", "◻️", "🔲", "⬜")
            return emojis[round((len(emojis) - 1) * weight / progress)]
        if weight < math.floor(rules.safe_weight * 0.99):
            return "🟦"
        if weight < rules.safe_weight:
            return "🟩"
        if weight == rules.safe_weight:
            return "✅"
        if weight <= rules.max_weight:
            return "🟨"
        return "⛔"


@attrs.frozen
class TypeIcons:
    none: Resource = _DEFAULT_RESOURCE
    torso: Resource = _DEFAULT_RESOURCE
    legs: Resource = _DEFAULT_RESOURCE
    drone: Resource = _DEFAULT_RESOURCE
    side_weapon: Resource = _DEFAULT_RESOURCE
    right_side_weapon: Resource = _DEFAULT_RESOURCE
    left_side_weapon: Resource = _DEFAULT_RESOURCE
    top_weapon: Resource = _DEFAULT_RESOURCE
    right_top_weapon: Resource = _DEFAULT_RESOURCE
    left_top_weapon: Resource = _DEFAULT_RESOURCE
    charge: Resource = _DEFAULT_RESOURCE
    teleport: Resource = _DEFAULT_RESOURCE
    hook: Resource = _DEFAULT_RESOURCE
    shield: Resource = _DEFAULT_RESOURCE
    module: Resource = _DEFAULT_RESOURCE
    perk: Resource = _DEFAULT_RESOURCE
    kit: Resource = _DEFAULT_RESOURCE

    def __getitem__(self, field: sm.abc.ItemType) -> Resource:
        return getattr(self, field)


@attrs.frozen
class Icons:
    types: TypeIcons = attrs.Factory(TypeIcons)


@attrs.frozen
class ElementColors:
    none: Color = _DEFAULT_COLOR
    physical: Color = _DEFAULT_COLOR
    explosive: Color = _DEFAULT_COLOR
    electric: Color = _DEFAULT_COLOR
    combined: Color = _DEFAULT_COLOR

    def __getitem__(self, field: sm.abc.ItemElement) -> Color:
        return getattr(self, field)


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
