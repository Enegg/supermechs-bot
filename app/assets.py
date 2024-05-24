"""Various assets existing on discord side."""

import math
import typing
from collections import abc

import attrs
import cattrs
from disnake import Color

from class_utlis import attrs_from_path
from config import CONFIG
from typeshed import T

from supermechs.api import BuildRules, Category, Element, Stat, Tier, Type

__all__ = ("ASSETS", "get_weight_emoji")


_converter = cattrs.Converter()
_converter.register_structure_hook(Category, lambda obj, cls: cls.of_name(obj))
_converter.register_structure_hook(Element, lambda obj, cls: cls.of_name(obj))
_converter.register_structure_hook(Stat, lambda obj, cls: cls.of_name(obj))
_converter.register_structure_hook(Tier, lambda obj, cls: cls.of_name(obj))
_converter.register_structure_hook(Type, lambda obj, cls: cls.of_name(obj))
_converter.register_structure_hook(Color, lambda obj, cls: cls(obj))


@attrs.define
class Asset:
    emoji: str = "❔"
    image_url: str = CONFIG.missing_image_url


@attrs.define
class ColoredAsset(Asset):
    color: Color = Color(0)
    emoji: str = "❔"
    image_url: str = CONFIG.missing_image_url


@attrs.define
class Sided(typing.Generic[T]):
    right: T
    left: T


@attrs.define(kw_only=True)
class Assets:
    stats: abc.Mapping[Stat, Asset]
    extra_stats: abc.Mapping[str, Asset]
    tiers: abc.Mapping[Tier, ColoredAsset]
    elements: abc.Mapping[Element, ColoredAsset]
    types: abc.Mapping[Type, Asset]
    sided_types: abc.Mapping[Type, Sided[Asset]]
    categories: abc.Mapping[Category, Asset]
    gifs: abc.Mapping[str, abc.Sequence[str]]


ASSETS = attrs_from_path("./assets/assets.toml", Assets, _converter)


def get_weight_emoji(weight: int, /, *, rules: BuildRules = CONFIG.game_rules.builds) -> str:
    if weight < 0:
        return "🗿"
    if weight < rules.MAX_WEIGHT * 0.99:
        return "⚙️"
    if weight < rules.MAX_WEIGHT:
        return "🆗"
    if weight == rules.MAX_WEIGHT:
        return "👌"
    if weight <= rules.OVERLOADED_MAX_WEIGHT:
        return "❕"
    return "⛔"


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
