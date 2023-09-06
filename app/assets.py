"""Various assets existing on discord side."""

import typing as t
import typing_extensions as tex
from typing import TYPE_CHECKING

from typeshed import T

from supermechs import constants
from supermechs.enums import Element, Tier, Type

if TYPE_CHECKING:
    from supermechs.models.item import TransformRange


class ColorEmojiAsset(t.NamedTuple):
    color: int
    emoji: tex.LiteralString


class TypeAsset(t.NamedTuple):
    image_url: str
    emoji: tex.LiteralString


class Sided(tex.NamedTuple, t.Generic[T]):
    right: T
    left: T


# fmt: off
TIER: t.Mapping[Tier, ColorEmojiAsset] = {
    Tier.COMMON:    ColorEmojiAsset(0xB1B1B1, "⚪"),
    Tier.RARE:      ColorEmojiAsset(0x55ACEE, "🔵"),
    Tier.EPIC:      ColorEmojiAsset(0xCC41CC, "🟣"),
    Tier.LEGENDARY: ColorEmojiAsset(0xE0A23C, "🟠"),
    Tier.MYTHICAL:  ColorEmojiAsset(0xFE6333, "🟤"),
    Tier.DIVINE:    ColorEmojiAsset(0xFFFFFF, "⚪"),
    Tier.PERK:      ColorEmojiAsset(0xFFFF33, "🟡"),
}
ELEMENT: t.Mapping[Element, ColorEmojiAsset] = {
    Element.PHYSICAL:  ColorEmojiAsset(0xFFB800, "<:phydmg:725871208830074929>"),
    Element.EXPLOSIVE: ColorEmojiAsset(0xB71010, "<:expdmg:725871223338172448>"),
    Element.ELECTRIC:  ColorEmojiAsset(0x106ED8, "<:eledmg:725871233614479443>"),
    Element.COMBINED:  ColorEmojiAsset(0x211D1D, "<:combined:1026853188940349490>"),
    Element.UNKNOWN:   ColorEmojiAsset(0x000000, "❔"),
}
TYPE: t.Mapping[Type, TypeAsset] = {
    Type.TORSO:    TypeAsset("https://i.imgur.com/iNtSziV.png",  "<:torso:730115680363347968>"),
    Type.LEGS:     TypeAsset("https://i.imgur.com/6NBLOhU.png",   "<:legs:730115699397361827>"),
    Type.DRONE:    TypeAsset("https://i.imgur.com/oqQmXTF.png",  "<:drone:730115574763618394>"),
    Type.TELEPORT: TypeAsset("https://i.imgur.com/Fnq035A.png",   "<:tele:730115603683213423>"),
    Type.CHARGE:   TypeAsset("https://i.imgur.com/UnDqJx8.png", "<:charge:730115557239685281>"),
    Type.HOOK:     TypeAsset("https://i.imgur.com/8oAoPcJ.png",   "<:hook:730115622347735071>"),
    Type.MODULE:   TypeAsset("https://i.imgur.com/dQR8UgN.png",    "<:mod:730115649866694686>"),
}
SIDED_TYPE: t.Mapping[t.Literal[Type.SIDE_WEAPON, Type.TOP_WEAPON], Sided[TypeAsset]] = {
    Type.SIDE_WEAPON: Sided(
        TypeAsset("https://i.imgur.com/CBbvOnQ.png", "<:sider:730115747799629940>"),
        TypeAsset("https://i.imgur.com/UuyYCrw.png", "<:sidel:730115729365663884>")
    ),
    Type.TOP_WEAPON: Sided(
        TypeAsset("https://i.imgur.com/LW7ZCGZ.png", "<:topr:730115786735091762>"),
        TypeAsset("https://i.imgur.com/1xlnVgK.png", "<:topl:730115768431280238>")
    ),
}
# fmt: on
STAT: t.Mapping[str, str] = {"weight": "<:weight:725870760484143174>"}  # TODO


def get_weight_emoji(weight: int, /) -> str:
    if weight < 0:
        return "🗿"
    if weight < constants.MAX_WEIGHT * 0.99:
        return "⚙️"
    if weight < constants.MAX_WEIGHT:
        return "🆗"
    if weight == constants.MAX_WEIGHT:
        return "👌"
    if weight <= constants.OVERLOADED_MAX_WEIGHT:
        return "❕"
    return "⛔"


def range_to_str(range: "TransformRange", /, at_tier: Tier | None = None) -> str:
    if at_tier is None:
        at_tier = range[-1]

    str_range = [str(tier) for tier in range]
    str_range[range.index(at_tier)] = f"({at_tier})"
    return "".join(str_range)
