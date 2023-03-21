from __future__ import annotations

import typing as t
from enum import Enum

from typing_extensions import Self

from .utils import MISSING

__all__ = ("Tier", "Element", "Type")


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


class Icon(t.NamedTuple):
    right: IconData
    left: IconData = MISSING

    @property
    def default(self) -> IconData:
        return self.right


class Tier(TierData, Enum):
    """Enumeration of item tiers."""

    _short_names2members: t.ClassVar[dict[str, Tier]]

    def __new__(cls, level: int, color: int, emoji: str) -> Self:
        obj = t.cast(Self, TierData.__new__(cls, level, color, emoji))
        obj._value_ = level
        return obj

    # fmt: off
    COMMON    = (0, 0xB1B1B1, "⚪")
    RARE      = (1, 0x55ACEE, "🔵")
    EPIC      = (2, 0xCC41CC, "🟣")
    LEGENDARY = (3, 0xE0A23C, "🟠")
    MYTHICAL  = (4, 0xFE6333, "🟤")
    DIVINE    = (5, 0xFFFFFF, "⚪")
    PERK      = (6, 0xFFFF33, "🟡")
    # fmt: on

    def __int__(self) -> int:
        return self.level

    @classmethod
    def from_letter(cls, letter: str) -> Tier:
        """Get enum member by the first letter of its name."""
        return cls._short_names2members[letter.upper()]


Tier._short_names2members = {tier.name[0]: tier for tier in Tier}


class Element(ElementData, Enum):
    """Enumeration of item elements."""

    # fmt: off
    PHYSICAL  = (0xFFB800, "<:phydmg:725871208830074929>")
    EXPLOSIVE = (0xB71010, "<:expdmg:725871223338172448>")
    ELECTRIC  = (0x106ED8, "<:eledmg:725871233614479443>")
    COMBINED  = (0x211D1D, "<:combined:1026853188940349490>")
    UNKNOWN   = (0x000000, "❔")
    # fmt: on


class Type(Icon, Enum):
    """Enumeration of item types."""

    # fmt: off
    TORSO       = (IconData("https://i.imgur.com/iNtSziV.png",  "<:torso:730115680363347968>"),)
    LEGS        = (IconData("https://i.imgur.com/6NBLOhU.png",   "<:legs:730115699397361827>"),)
    DRONE       = (IconData("https://i.imgur.com/oqQmXTF.png",  "<:drone:730115574763618394>"),)
    SIDE_WEAPON = (IconData("https://i.imgur.com/CBbvOnQ.png",  "<:sider:730115747799629940>"),
                   IconData("https://i.imgur.com/UuyYCrw.png",  "<:sidel:730115729365663884>"))
    TOP_WEAPON  = (IconData("https://i.imgur.com/LW7ZCGZ.png",   "<:topr:730115786735091762>"),
                   IconData("https://i.imgur.com/1xlnVgK.png",   "<:topl:730115768431280238>"))
    TELEPORTER  = (IconData("https://i.imgur.com/Fnq035A.png",   "<:tele:730115603683213423>"),)
    CHARGE      = (IconData("https://i.imgur.com/UnDqJx8.png", "<:charge:730115557239685281>"),)
    HOOK        = (IconData("https://i.imgur.com/8oAoPcJ.png",   "<:hook:730115622347735071>"),)
    MODULE      = (IconData("https://i.imgur.com/dQR8UgN.png",    "<:mod:730115649866694686>"),)
    CHARGE_ENGINE = CHARGE
    GRAPPLING_HOOK = HOOK
    TELE = TELEPORTER
    # SHIELD, PERK, KIT?
    # fmt: on

    @property
    def emoji(self) -> str:
        return self.default.emoji

    @property
    def image_url(self) -> str:
        return self.default.image_url

    @property
    def displayable(self) -> bool:
        """True if the type can be rendered on a mech, False otherwise"""
        return self.name not in ("TELEPORTER", "CHARGE", "HOOK", "MODULE")

    @property
    def attachable(self) -> bool:
        """True if the type should have an attachment, False otherwise"""
        return self.displayable and self.name != "DRONE"
