"""Various assets existing on discord side."""

import math
from collections import abc
from typing import Generic

import attrs
import cattrs

from disnake import Color

from app import paths
from app.class_utils import MappingParser
from app.core import CONFIG
from app.typeshed import T
from resources import Resource

from supermechs.gamerules import BuildRules

__all__ = ("ASSETS", "get_weight_emoji")


@cattrs.global_converter.register_structure_hook
def _structure_color(value: int, cls: type) -> Color:
    return Color(int(value))


@cattrs.global_converter.register_structure_hook
def _structure_resource(value: str, cls: type) -> Resource:
    assert isinstance(value, str)
    return Resource.from_uri(value)


del _structure_color, _structure_resource


@attrs.frozen
class Asset:
    emoji: str = "❔"
    resource: Resource = Resource.from_uri(CONFIG.missing_image_url)


@attrs.frozen
class ColoredAsset(Asset):
    color: Color = Color(0)


@attrs.frozen
class Sided(Generic[T]):
    right: T
    left: T


@attrs.frozen
class Assets:
    stats: abc.Mapping[str, Asset]
    extra_stats: abc.Mapping[str, Asset]
    tiers: abc.Mapping[str, ColoredAsset]
    elements: abc.Mapping[str, ColoredAsset]
    types: abc.Mapping[str, Asset]
    sided_types: abc.Mapping[str, Sided[Asset]]
    categories: abc.Mapping[str, Asset]
    frantic_gifs: abc.Sequence[str]


ASSETS = MappingParser.from_path(paths.ASSETS_TOML).structure(Assets)


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
