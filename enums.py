from __future__ import annotations

from enum import Enum
from typing import Iterator, NamedTuple


WORKSHOP_STATS: dict[str, type[int]] = dict(
    weight=int,
    health=int,
    eneCap=int,
    eneReg=int,
    heaCap=int,
    heaCol=int,
    phyRes=int,
    expRes=int,
    eleRes=int,
    bulletCap=int,
    rocketCap=int,
    walk=int,
    jump=int)


class Stat(NamedTuple):
    name: str
    emoji: str


class Tier(NamedTuple):
    level: int
    color: int
    emoji: str


class Element(NamedTuple):
    color: int
    emoji: str


class Icon(NamedTuple):
    URL: str
    emoji: str


STAT_NAMES = dict(
       weight=Stat('Weight',                   '<:weight:725870760484143174>'),
       health=Stat('HP',                       '<:health:725870887588462652>'),
       eneCap=Stat('Energy',                   '<:energy:725870941883859054>'),
       eneReg=Stat('Regeneration',              '<:regen:725871003665825822>'),
       heaCap=Stat('Heat',                       '<:heat:725871043767435336>'),
       heaCol=Stat('Cooling',                 '<:cooling:725871075778363422>'),
       phyRes=Stat('Physical resistance',      '<:phyres:725871121051811931>'),
       expRes=Stat('Explosive resistance',     '<:expres:725871136935772294>'),
       eleRes=Stat('Electric resistance',     '<:elecres:725871146716758077>'),
       phyDmg=Stat('Damage',                   '<:phydmg:725871208830074929>'),
    phyResDmg=Stat('Resistance drain',      '<:phyresdmg:725871259635679263>'),
       expDmg=Stat('Damage',                   '<:expdmg:725871223338172448>'),
       heaDmg=Stat('Heat damage',              '<:headmg:725871613639393290>'),
    heaCapDmg=Stat('Heat capacity drain',  '<:heatcapdmg:725871478083551272>'),
    heaColDmg=Stat('Cooling damage',       '<:coolingdmg:725871499281563728>'),
    expResDmg=Stat('Resistance drain',      '<:expresdmg:725871281311842314>'),
       eleDmg=Stat('Damage',                   '<:eledmg:725871233614479443>'),
       eneDmg=Stat('Energy drain',             '<:enedmg:725871599517171719>'),
    eneCapDmg=Stat('Energy capacity drain', '<:enecapdmg:725871420126789642>'),
    eneRegDmg=Stat('Regeneration damage',    '<:regendmg:725871443815956510>'),
    eleResDmg=Stat('Resistance drain',      '<:eleresdmg:725871296381976629>'),
        range=Stat('Range',                     '<:range:725871752072134736>'),
         push=Stat('Knockback',                  '<:push:725871716613488843>'),
         pull=Stat('Pull',                       '<:pull:725871734141616219>'),
       recoil=Stat('Recoil',                   '<:recoil:725871778282340384>'),
      retreat=Stat('Retreat',                 '<:retreat:725871804236955668>'),
      advance=Stat('Advance',                 '<:advance:725871818115907715>'),
         walk=Stat('Walking',                    '<:walk:725871844581834774>'),
         jump=Stat('Jumping',                    '<:jump:725871869793796116>'),
         uses=Stat('Uses',                       '<:uses:725871917923303688>'),
     backfire=Stat('Backfire',               '<:backfire:725871901062201404>'),
      heaCost=Stat('Heat cost',               '<:heatgen:725871674007879740>'),
      eneCost=Stat('Energy cost',            '<:eneusage:725871660237979759>'))


class Rarity(Enum):
    """Enumeration of item tiers"""
    value: Tier

    COMMON    = C = Tier(0, 0xB1B1B1, '⚪')
    RARE      = R = Tier(1, 0x55ACEE, '🔵')
    EPIC      = E = Tier(2, 0xCC41CC, '🟣')
    LEGENDARY = L = Tier(3, 0xE0A23C, '🟠')
    MYTHICAL  = M = Tier(4, 0xFE6333, '🟤')
    DIVINE    = D = Tier(5, 0xFFFFFF, '⚪')
    PERK      = P = Tier(6, 0xFFFF33, '🟡')

    def __str__(self) -> str:
        return self.emoji

    def __int__(self) -> int:
        return self.level

    @property
    def level(self) -> int:
        return self.value.level

    @property
    def color(self) -> int:
        return self.value.color

    @property
    def emoji(self) -> str:
        return self.value.emoji

    def __gt__(self, o: object) -> bool:
        if not isinstance(o, Rarity):
            return NotImplemented

        return self.level > o.level

    def __lt__(self, o: object) -> bool:
        if not isinstance(o, Rarity):
            return NotImplemented

        return self.level < o.level

    def next_tier(self) -> Rarity:
        for rarity in Rarity:
            if rarity.level == self.level + 1:
                return rarity

        raise TypeError('Highest rarity already achieved')


class RarityRange:
    TIERS = tuple(Rarity)

    def __init__(self, lower: Rarity | int, upper: Rarity | int = None) -> None:
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
                raise ValueError('upper rarity below lower rarity')

            raise ValueError('rarities out of bounds')

        self.range = range(lower, upper+1)

    def __str__(self) -> str:
        return ''.join(rarity.emoji for rarity in self)

    def __repr__(self) -> str:
        return f'RarityRange(Rarity.{self.min.name}, Rarity.{self.max.name})'

    def __iter__(self) -> Iterator[Rarity]:
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
    def from_string(cls, string: str) -> RarityRange:
        up, _, down = string.strip().partition('-')

        if down:
            return cls(Rarity[up.upper()], Rarity[down.upper()])

        return cls(Rarity[up.upper()])


class Elements(Enum):
    """Enumeration of item elements"""
    value: Element

    PHYSICAL  = PHYS = Element(0xffb800, STAT_NAMES['phyDmg'].emoji)
    EXPLOSIVE = HEAT = Element(0xb71010, STAT_NAMES['expDmg'].emoji)
    ELECTRIC  = ELEC = Element(0x106ed8, STAT_NAMES['eleDmg'].emoji)
    COMBINED  = COMB = Element(0x211d1d, '🔰')
    OMNI =             Element(0x000000, '<a:energyball:731885130594910219>')

    def __str__(self) -> str:
        return self.emoji

    @property
    def color(self) -> int:
        return self.value.color

    @property
    def emoji(self) -> str:
        return self.value.emoji


class Icons(Enum):
    """Enumeration of item types"""
    value: Icon

    TORSO       = Icon('https://i.imgur.com/iNtSziV.png',  '<:torso:730115680363347968>')
    LEGS        = Icon('https://i.imgur.com/6NBLOhU.png',   '<:legs:730115699397361827>')
    DRONE       = Icon('https://i.imgur.com/oqQmXTF.png',  '<:drone:730115574763618394>')
    SIDE_WEAPON = Icon('https://i.imgur.com/CBbvOnQ.png',  '<:sider:730115747799629940>')
    SIDE_LEFT   = Icon('https://i.imgur.com/UuyYCrw.png',  '<:sidel:730115729365663884>')
    TOP_WEAPON  = Icon('https://i.imgur.com/LW7ZCGZ.png',   '<:topr:730115786735091762>')
    TOP_LEFT    = Icon('https://i.imgur.com/1xlnVgK.png',   '<:topl:730115768431280238>')
    TELE        = Icon('https://i.imgur.com/Fnq035A.png',   '<:tele:730115603683213423>')
    CHARGE      = Icon('https://i.imgur.com/UnDqJx8.png', '<:charge:730115557239685281>')
    HOOK        = Icon('https://i.imgur.com/8oAoPcJ.png',   '<:hook:730115622347735071>')
    MODULE      = Icon('https://i.imgur.com/dQR8UgN.png',    '<:mod:730115649866694686>')
    SIDE_RIGHT = SIDE_WEAPON
    TOP_RIGHT = TOP_WEAPON
    CHARGE_ENGINE = CHARGE
    GRAPPLING_HOOK = HOOK
    TELEPORTER = TELE
    # SHIELD
    # PERK
    # KIT

    def __str__(self) -> str:
        return self.emoji

    @property
    def URL(self) -> str:
        return self.value.URL

    @property
    def emoji(self) -> str:
        return self.value.emoji
