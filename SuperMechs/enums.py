from __future__ import annotations

import typing as t
from enum import Enum

from utils import MISSING


class TierData(t.NamedTuple):
    level: int
    color: int
    emoji: str

    def __str__(self) -> str:
        return self.emoji

    def __int__(self) -> int:
        return self.level


class ElementData(t.NamedTuple):
    color: int
    emoji: str

    def __str__(self) -> str:
        return self.emoji


class IconData(t.NamedTuple):
    image_url: str
    emoji: str
    alt: IconData = MISSING

    def __str__(self) -> str:
        return self.emoji


class Rarity(TierData, Enum):
    """Enumeration of item tiers"""

    # fmt: off
    COMMON    = C = TierData(0, 0xB1B1B1, "⚪")
    RARE      = R = TierData(1, 0x55ACEE, "🔵")
    EPIC      = E = TierData(2, 0xCC41CC, "🟣")
    LEGENDARY = L = TierData(3, 0xE0A23C, "🟠")
    MYTHICAL  = M = TierData(4, 0xFE6333, "🟤")
    DIVINE    = D = TierData(5, 0xFFFFFF, "⚪")
    PERK      = P = TierData(6, 0xFFFF33, "🟡")
    # fmt: on

    def __int__(self) -> int:
        return self.level


class Element(ElementData, Enum):
    """Enumeration of item elements"""

    # fmt: off
    PHYSICAL  = PHYS = ElementData(0xffb800, "<:phydmg:725871208830074929>")
    EXPLOSIVE = HEAT = ElementData(0xb71010, "<:expdmg:725871223338172448>")
    ELECTRIC  = ELEC = ElementData(0x106ed8, "<:eledmg:725871233614479443>")
    COMBINED  = COMB = ElementData(0x211d1d, "🔰")
    OMNI =             ElementData(0x000000, "<a:energyball:731885130594910219>")
    # fmt: on


class Type(IconData, Enum):
    """Enumeration of item types"""

    # fmt: off
    TORSO       = IconData("https://i.imgur.com/iNtSziV.png",  "<:torso:730115680363347968>")
    LEGS        = IconData("https://i.imgur.com/6NBLOhU.png",   "<:legs:730115699397361827>")
    DRONE       = IconData("https://i.imgur.com/oqQmXTF.png",  "<:drone:730115574763618394>")
    SIDE_WEAPON = IconData("https://i.imgur.com/CBbvOnQ.png",  "<:sider:730115747799629940>",
                  IconData("https://i.imgur.com/UuyYCrw.png",  "<:sidel:730115729365663884>"))
    TOP_WEAPON  = IconData("https://i.imgur.com/LW7ZCGZ.png",   "<:topr:730115786735091762>",
                  IconData("https://i.imgur.com/1xlnVgK.png",   "<:topl:730115768431280238>"))
    TELEPORTER  = IconData("https://i.imgur.com/Fnq035A.png",   "<:tele:730115603683213423>")
    CHARGE      = IconData("https://i.imgur.com/UnDqJx8.png", "<:charge:730115557239685281>")
    HOOK        = IconData("https://i.imgur.com/8oAoPcJ.png",   "<:hook:730115622347735071>")
    MODULE      = IconData("https://i.imgur.com/dQR8UgN.png",    "<:mod:730115649866694686>")
    CHARGE_ENGINE = CHARGE
    GRAPPLING_HOOK = HOOK
    TELE = TELEPORTER
    # SHIELD, PERK, KIT?
    # fmt: on

    @property
    def displayable(self) -> bool:
        """True if the type can be rendered on a mech, False otherwise"""
        return self.name not in ("TELEPORTER", "CHARGE", "HOOK", "MODULE")

    @property
    def attachable(self) -> bool:
        """True if the type should have an attachment, False otherwise"""
        return self.displayable and self.name != "DRONE"
