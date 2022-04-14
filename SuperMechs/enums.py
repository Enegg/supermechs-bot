from __future__ import annotations

import typing as t
from enum import Enum

WORKSHOP_STATS: t.Final = (
    "weight", "health", "eneCap", "eneReg", "heaCap", "heaCol", "phyRes",
    "expRes", "eleRes", "bulletCap", "rocketCap", "walk", "jump")


class Stat(t.NamedTuple):
    name: str
    emoji: str


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

    def __str__(self) -> str:
        return self.emoji


# fmt: off
STAT_NAMES = dict(
    weight   =Stat("Weight",                "<:weight:725870760484143174>"),
    health   =Stat("HP",                    "<:health:725870887588462652>"),
    eneCap   =Stat("Energy",                "<:energy:725870941883859054>"),
    eneReg   =Stat("Regeneration",           "<:regen:725871003665825822>"),
    heaCap   =Stat("Heat",                    "<:heat:725871043767435336>"),
    heaCol   =Stat("Cooling",              "<:cooling:725871075778363422>"),
    phyRes   =Stat("Physical resistance",   "<:phyres:725871121051811931>"),
    expRes   =Stat("Explosive resistance",  "<:expres:725871136935772294>"),
    eleRes   =Stat("Electric resistance",  "<:elecres:725871146716758077>"),
    phyDmg   =Stat("Physical damage",       "<:phydmg:725871208830074929>"),
    phyResDmg=Stat("Resistance drain",   "<:phyresdmg:725871259635679263>"),
    expDmg   =Stat("Explosive damage",      "<:expdmg:725871223338172448>"),
    heaDmg   =Stat("Heat damage",           "<:headmg:725871613639393290>"),
    heaCapDmg=Stat("Max heat damage",   "<:heatcapdmg:725871478083551272>"),
    heaColDmg=Stat("Cooling damage",    "<:coolingdmg:725871499281563728>"),
    expResDmg=Stat("Resistance drain",   "<:expresdmg:725871281311842314>"),
    eleDmg   =Stat("Electric damage",       "<:eledmg:725871233614479443>"),
    eneDmg   =Stat("Energy damage",         "<:enedmg:725871599517171719>"),
    eneCapDmg=Stat("Max energy damage",  "<:enecapdmg:725871420126789642>"),
    eneRegDmg=Stat("Regeneration damage", "<:regendmg:725871443815956510>"),
    eleResDmg=Stat("Resistance drain",   "<:eleresdmg:725871296381976629>"),
    range    =Stat("Range",                  "<:range:725871752072134736>"),
    push     =Stat("Knockback",               "<:push:725871716613488843>"),
    pull     =Stat("Pull",                    "<:pull:725871734141616219>"),
    recoil   =Stat("Recoil",                "<:recoil:725871778282340384>"),
    retreat  =Stat("Retreat",              "<:retreat:725871804236955668>"),
    advance  =Stat("Advance",              "<:advance:725871818115907715>"),
    walk     =Stat("Walking",                 "<:walk:725871844581834774>"),
    jump     =Stat("Jumping",                 "<:jump:725871869793796116>"),
    uses     =Stat("Uses",                    "<:uses:725871917923303688>"),
    backfire =Stat("Backfire",            "<:backfire:725871901062201404>"),
    heaCost  =Stat("Heat cost",            "<:heatgen:725871674007879740>"),
    eneCost  =Stat("Energy cost",         "<:eneusage:725871660237979759>"))
# fmt: on


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


class RarityRange:
    TIERS = tuple(Rarity)

    def __init__(self, lower: Rarity | int, upper: Rarity | int | None = None) -> None:
        """Represents a range of rarities an item can have. Unlike `range` object,
        upper bound is inclusive."""

        if isinstance(lower, Rarity):
            lower = lower.level

        if upper is None:
            upper = lower

        elif isinstance(upper, Rarity):
            upper = upper.level

        if not 0 <= lower <= upper <= self.TIERS[-1].level:
            if lower > upper:
                raise ValueError("upper rarity below lower rarity")

            raise ValueError("rarities out of bounds")

        self.range = range(lower, upper+1)

    def __str__(self) -> str:
        return "".join(rarity.emoji for rarity in self)

    def __repr__(self) -> str:
        return f"RarityRange(Rarity.{self.min.name}, Rarity.{self.max.name})"

    def __iter__(self) -> t.Iterator[Rarity]:
        return (self.TIERS[n] for n in self.range)

    def __eq__(self, obj: object) -> bool:
        if not isinstance(obj, RarityRange):
            return NotImplemented

        return self.range == obj.range

    def __len__(self) -> int:
        return len(self.range)

    @property
    def min(self) -> Rarity:
        """Lower rarity bound"""
        return self.TIERS[self.range.start]

    @property
    def max(self) -> Rarity:
        """Upper rarity bound"""
        return self.TIERS[self.range.stop-1]

    @property
    def is_single(self) -> bool:
        """Whether range has only one rarity"""
        return len(self.range) == 1

    def __contains__(self, item: Rarity | RarityRange) -> bool:
        match item:
            case Rarity():
                return item.level in self.range

            case RarityRange():
                return item.range in self.range

            case _:
                return NotImplemented

    @classmethod
    def from_string(cls, string: str, /) -> RarityRange:
        up, _, down = string.strip().partition("-")

        if down:
            return cls(Rarity[up.upper()], Rarity[down.upper()])

        return cls(Rarity[up.upper()])

    def next_tier(self, current: Rarity, /) -> Rarity:
        if current is self.TIERS[-1] or current is self.max:
            raise TypeError("Highest rarity already achieved")

        return self.TIERS[self.TIERS.index(current) + 1]


class Element(ElementData, Enum):
    """Enumeration of item elements"""
    # fmt: off
    PHYSICAL  = PHYS = ElementData(0xffb800, STAT_NAMES["phyDmg"].emoji)
    EXPLOSIVE = HEAT = ElementData(0xb71010, STAT_NAMES["expDmg"].emoji)
    ELECTRIC  = ELEC = ElementData(0x106ed8, STAT_NAMES["eleDmg"].emoji)
    COMBINED  = COMB = ElementData(0x211d1d, "🔰")
    OMNI =             ElementData(0x000000, "<a:energyball:731885130594910219>")
    # fmt: on


class Icon(IconData, Enum):
    """Enumeration of item types"""
    # fmt: off
    TORSO       = IconData("https://i.imgur.com/iNtSziV.png",  "<:torso:730115680363347968>")
    LEGS        = IconData("https://i.imgur.com/6NBLOhU.png",   "<:legs:730115699397361827>")
    DRONE       = IconData("https://i.imgur.com/oqQmXTF.png",  "<:drone:730115574763618394>")
    SIDE_WEAPON = IconData("https://i.imgur.com/CBbvOnQ.png",  "<:sider:730115747799629940>")
    SIDE_LEFT   = IconData("https://i.imgur.com/UuyYCrw.png",  "<:sidel:730115729365663884>")
    TOP_WEAPON  = IconData("https://i.imgur.com/LW7ZCGZ.png",   "<:topr:730115786735091762>")
    TOP_LEFT    = IconData("https://i.imgur.com/1xlnVgK.png",   "<:topl:730115768431280238>")
    TELE        = IconData("https://i.imgur.com/Fnq035A.png",   "<:tele:730115603683213423>")
    CHARGE      = IconData("https://i.imgur.com/UnDqJx8.png", "<:charge:730115557239685281>")
    HOOK        = IconData("https://i.imgur.com/8oAoPcJ.png",   "<:hook:730115622347735071>")
    MODULE      = IconData("https://i.imgur.com/dQR8UgN.png",    "<:mod:730115649866694686>")
    SIDE_RIGHT = SIDE_WEAPON
    TOP_RIGHT = TOP_WEAPON
    CHARGE_ENGINE = CHARGE
    GRAPPLING_HOOK = HOOK
    TELEPORTER = TELE
    # SHIELD, PERK, KIT?
    # fmt: on
