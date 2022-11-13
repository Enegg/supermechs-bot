from __future__ import annotations

import typing as t
from enum import Enum

from typing_extensions import Self

from .utils import MISSING


class TierData(t.NamedTuple):
    level: int
    color: int
    emoji: str


class ElementData(t.NamedTuple):
    color: int
    emoji: str


class IconData(t.NamedTuple):
    image_url: str
    emoji: str
    alt: IconData = MISSING


class Tier(TierData, Enum):
    """Enumeration of item tiers."""

    def __new__(cls, level: int, color: int, emoji: str) -> Self:
        obj = t.cast(Self, TierData.__new__(cls, level, color, emoji))
        obj._value_ = level
        return obj

    # fmt: off
    COMMON    = C = (0, 0xB1B1B1, "⚪")
    RARE      = R = (1, 0x55ACEE, "🔵")
    EPIC      = E = (2, 0xCC41CC, "🟣")
    LEGENDARY = L = (3, 0xE0A23C, "🟠")
    MYTHICAL  = M = (4, 0xFE6333, "🟤")
    DIVINE    = D = (5, 0xFFFFFF, "⚪")
    PERK      = P = (6, 0xFFFF33, "🟡")
    # fmt: on

    def __int__(self) -> int:
        return self.level


class Element(ElementData, Enum):
    """Enumeration of item elements."""

    # fmt: off
    PHYSICAL  = PHYS = (0xffb800, "<:phydmg:725871208830074929>")
    EXPLOSIVE = HEAT = (0xb71010, "<:expdmg:725871223338172448>")
    ELECTRIC  = ELEC = (0x106ed8, "<:eledmg:725871233614479443>")
    COMBINED  = COMB = (0x211d1d, "<:combined:1026853188940349490>")
    OMNI =             (0x000000, "<a:energyball:731885130594910219>")
    # fmt: on


class Type(IconData, Enum):
    """Enumeration of item types."""

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
