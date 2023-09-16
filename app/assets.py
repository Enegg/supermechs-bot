"""Various assets existing on discord side."""

import typing as t
import typing_extensions as tex
from typing import TYPE_CHECKING

from typeshed import T

from supermechs import constants
from supermechs.enums import Element, Tier, Type

if TYPE_CHECKING:
    from supermechs.models.item import TransformRange

__all__ = (
    "ELEMENT", "FRANTIC_GIFS", "SIDED_TYPE", "STAT", "TIER", "TYPE",
    "get_weight_emoji", "range_to_str",
)


class ColorEmojiAsset(t.NamedTuple):
    color: int
    emoji: tex.LiteralString


class TypeAsset(t.NamedTuple):
    image_url: tex.LiteralString
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
STAT: t.Mapping[str, tex.LiteralString] = {
    "weight":          "<:weight:725870760484143174>",
    "health":          "<:health:725870887588462652>",
    "eneCap":          "<:energy:725870941883859054>",
    "eneReg":           "<:regen:725871003665825822>",
    "heaCap":            "<:heat:725871043767435336>",
    "heaCol":         "<:cooling:725871075778363422>",
    "bulletsCap": "🧰",
    "rocketsCap": "🧰",
    "phyRes":          "<:phyres:725871121051811931>",
    "expRes":          "<:expres:725871136935772294>",
    "eleRes":         "<:elecres:725871146716758077>",
    "phyDmg":          "<:phydmg:725871208830074929>",
    "phyResDmg":    "<:phyresdmg:725871259635679263>",
    "expDmg":          "<:expdmg:725871223338172448>",
    "heaDmg":          "<:headmg:725871613639393290>",
    "heaCapDmg":   "<:heatcapdmg:725871478083551272>",
    "heaColDmg":   "<:coolingdmg:725871499281563728>",
    "expResDmg":    "<:expresdmg:725871281311842314>",
    "eleDmg":          "<:eledmg:725871233614479443>",
    "eneDmg":          "<:enedmg:725871599517171719>",
    "eneCapDmg":    "<:enecapdmg:725871420126789642>",
    "eneRegDmg":     "<:regendmg:725871443815956510>",
    "eleResDmg":    "<:eleresdmg:725871296381976629>",
    "range":            "<:range:725871752072134736>",
    "push":              "<:push:725871716613488843>",
    "pull":              "<:pull:725871734141616219>",
    "recoil":          "<:recoil:725871778282340384>",
    "retreat":        "<:retreat:725871804236955668>",
    "advance":        "<:advance:725871818115907715>",
    "walk":              "<:walk:725871844581834774>",
    "jump":              "<:jump:725871869793796116>",
    "uses":              "<:uses:725871917923303688>",
    "backfire":      "<:backfire:725871901062201404>",
    "heaCost":        "<:heatgen:725871674007879740>",
    "eneCost":       "<:eneusage:725871660237979759>",
    "bulletsCost": "🥕",
    "rocketsCost": "🚀",
    "anyDmg":       "<:combined:1026853188940349490>",
}
# fmt: on
FRANTIC_GIFS: t.Sequence[tex.LiteralString] = (
    "https://i.imgur.com/Bbbf4AH.mp4",
    "https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4"
)

def get_weight_emoji(weight: int, /) -> tex.LiteralString:
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

    index = at_tier.order - range[0].order
    str_range = [TIER[tier].emoji for tier in range]
    str_range[index] = f"({str_range[index]})"
    return "".join(str_range)
