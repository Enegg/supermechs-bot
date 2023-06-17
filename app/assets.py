"""Various assets existing on discord side."""

import typing as t

from disnake.utils import MISSING

from supermechs.enums import Element, Tier, Type


class TierData(t.NamedTuple):
    color: int
    emoji: str

# fmt: off
TIER_ASSETS: t.Mapping[Tier, TierData] = {
    Tier.COMMON:    TierData(0xB1B1B1, "⚪"),
    Tier.RARE:      TierData(0x55ACEE, "🔵"),
    Tier.EPIC:      TierData(0xCC41CC, "🟣"),
    Tier.LEGENDARY: TierData(0xE0A23C, "🟠"),
    Tier.MYTHICAL:  TierData(0xFE6333, "🟤"),
    Tier.DIVINE:    TierData(0xFFFFFF, "⚪"),
    Tier.PERK:      TierData(0xFFFF33, "🟡"),
}
# fmt: on


class ElementData(t.NamedTuple):
    color: int
    emoji: str


# fmt: off
ELEMENT_ASSETS: t.Mapping[Element, ElementData] = {
    Element.PHYSICAL:  ElementData(0xFFB800, "<:phydmg:725871208830074929>"),
    Element.EXPLOSIVE: ElementData(0xB71010, "<:expdmg:725871223338172448>"),
    Element.ELECTRIC:  ElementData(0x106ED8, "<:eledmg:725871233614479443>"),
    Element.COMBINED:  ElementData(0x211D1D, "<:combined:1026853188940349490>"),
    Element.UNKNOWN:   ElementData(0x000000, "❔"),
}
# fmt: on


class IconData(t.NamedTuple):
    image_url: str
    emoji: str


class Icon(t.NamedTuple):
    right: IconData
    left: IconData = MISSING

    @property
    def default(self) -> IconData:
        return self.right


IMGUR_URL_BASE = "https://i.imgur.com/{}.png"


# fmt: off
TYPE_ASSETS: t.Mapping[Type, Icon] = {
    Type.TORSO: Icon(IconData("https://i.imgur.com/iNtSziV.png", "<:torso:730115680363347968>")),
    Type.LEGS:  Icon(IconData("https://i.imgur.com/6NBLOhU.png",  "<:legs:730115699397361827>")),
    Type.DRONE: Icon(IconData("https://i.imgur.com/oqQmXTF.png", "<:drone:730115574763618394>")),
    Type.SIDE_WEAPON: Icon(
        IconData("https://i.imgur.com/CBbvOnQ.png", "<:sider:730115747799629940>"),
        IconData("https://i.imgur.com/UuyYCrw.png", "<:sidel:730115729365663884>")
    ),
    Type.TOP_WEAPON: Icon(
        IconData("https://i.imgur.com/LW7ZCGZ.png", "<:topr:730115786735091762>"),
        IconData("https://i.imgur.com/1xlnVgK.png", "<:topl:730115768431280238>")
    ),
    Type.TELE:   Icon(IconData("https://i.imgur.com/Fnq035A.png",   "<:tele:730115603683213423>")),
    Type.CHARGE: Icon(IconData("https://i.imgur.com/UnDqJx8.png", "<:charge:730115557239685281>")),
    Type.HOOK:   Icon(IconData("https://i.imgur.com/8oAoPcJ.png",   "<:hook:730115622347735071>")),
    Type.MODULE: Icon(IconData("https://i.imgur.com/dQR8UgN.png",    "<:mod:730115649866694686>")),
}
# fmt: on
