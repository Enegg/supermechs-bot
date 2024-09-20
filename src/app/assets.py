"""Various assets existing on discord side."""

import math
from collections import abc
from typing import Final, Generic

import attrs
import cattrs

from disnake import Color

from app import paths
from app.class_utils import attrs_from_path
from app.core import CONFIG
from app.typeshed import T

from supermechs.api import BuildRules

__all__ = ("ASSETS", "get_weight_emoji")

INVISIBLE_CHAR: Final = "\u2800"
"""Invisible character discord does not truncate."""

_converter = cattrs.Converter()
_converter.register_structure_hook(Color, lambda obj, cls: cls(obj))


@attrs.frozen
class Asset:
    emoji: str = "❔"
    image_url: str = CONFIG.missing_image_url


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
    weight_0: str
    weight_1: str
    weight_2: str
    weight_3: str
    weight_4: str
    weight_99: str
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
    emojis: Emojis
    gifs: abc.Mapping[str, abc.Sequence[str]]


ASSETS = attrs_from_path(Assets, paths.ASSETS, _converter)
EMOJIS = ASSETS.emojis


def get_weight_emoji(weight: int, /, *, rules: BuildRules = CONFIG.game_rules.builds) -> str:
    if weight < 0:
        return EMOJIS.weight_sub_0
    close = math.floor(rules.MAX_WEIGHT * 0.99)
    if weight < close:
        emojis = (
            "",
            EMOJIS.weight_0,
            EMOJIS.weight_1,
            EMOJIS.weight_2,
            EMOJIS.weight_3,
            EMOJIS.weight_4,
        )
        return emojis[round((len(emojis) - 1) * weight / close)]
    if weight < rules.MAX_WEIGHT:
        return EMOJIS.weight_99
    if weight == rules.MAX_WEIGHT:
        return EMOJIS.weight_1k
    if weight <= rules.OVERLOADED_MAX_WEIGHT:
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
