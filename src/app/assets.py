"""Various assets existing on discord side."""

import math
from collections import abc
from typing import Final, Generic

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

INVISIBLE_CHAR: Final = "\u2800"
"""Invisible character discord does not truncate."""

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
class Emojis:
    weight_sub_0: str
    weight_stages: tuple[str, ...]
    weight_900: str
    weight_990: str
    weight_1k: str
    overload: str
    overweight: str


@attrs.frozen
class Assets:
    stats: abc.Mapping[str, Asset]
    extra_stats: abc.Mapping[str, Asset]
    tiers: abc.Mapping[str, ColoredAsset]
    elements: abc.Mapping[str, ColoredAsset]
    types: abc.Mapping[str, Asset]
    sided_types: abc.Mapping[str, Sided[Asset]]
    categories: abc.Mapping[str, Asset]
    gifs: abc.Mapping[str, abc.Sequence[str]]


_config = MappingParser.from_path(paths.ASSETS_TOML)
ASSETS = _config.structure(Assets)
EMOJIS = _config.structure(Emojis, "emojis")
del _config


def get_weight_emoji(weight: int, /, *, rules: BuildRules = CONFIG.build_rules) -> str:
    if weight < 0:
        return EMOJIS.weight_sub_0
    progress = math.floor(rules.safe_weight * 0.9)
    if weight < progress:
        emojis = ("", *EMOJIS.weight_stages)
        return emojis[round((len(emojis) - 1) * weight / progress)]
    if weight < math.floor(rules.safe_weight * 0.99):
        return EMOJIS.weight_900
    if weight < rules.safe_weight:
        return EMOJIS.weight_990
    if weight == rules.safe_weight:
        return EMOJIS.weight_1k
    if weight <= rules.max_weight:
        return EMOJIS.overload
    return EMOJIS.overweight


def blend_colors1(*colors: Color) -> Color:
    # https://stackoverflow.com/a/1351485
    return Color.from_rgb(
        round(255 - math.sqrt(sum((255 - color.r) ** 2 for color in colors) / len(colors))),
        round(255 - math.sqrt(sum((255 - color.g) ** 2 for color in colors) / len(colors))),
        round(255 - math.sqrt(sum((255 - color.b) ** 2 for color in colors) / len(colors))),
    )


def blend_colors2(*colors: Color) -> Color:
    return Color.from_rgb(
        sum(color.r for color in colors) // len(colors),
        sum(color.g for color in colors) // len(colors),
        sum(color.b for color in colors) // len(colors),
    )
