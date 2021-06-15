from __future__ import annotations


from dataclasses import dataclass
from enum import Enum
from itertools import zip_longest
from types import GenericAlias
from typing import *  # type: ignore


class AnyStats(TypedDict, total=False):
    weight: int
    health: int
    eneCap: int
    eneReg: int
    heaCap: int
    heaCol: int
    bulletCap: int
    rocketCap: int
    phyRes: int
    expRes: int
    eleRes: int
    phyDmg: tuple[int, int]
    phyResDmg: int
    eleDmg: tuple[int, int]
    eneDmg: int
    eneCapDmg: int
    eneRegDmg: int
    eleResDmg: int
    expDmg: tuple[int, int]
    heaDmg: int
    heaCapDmg: int
    heaColDmg: int
    expResDmg: int
    walk: int
    jump: int
    range: tuple[int, int]
    push: int
    pull: int
    recoil: int
    advance: int
    retreat: int
    uses: int
    backfire: int
    heaCost: int
    eneCost: int
    bulletCost: int
    rocketCost: int



class ItemDict(TypedDict):
    id: int
    name: str
    image: str
    type: str
    element: str
    transform_range: str
    stats:  AnyStats
    divine: AnyStats
    tags: list[str]
    attachment: dict[str, dict[str, int]]



class Tier(NamedTuple):
    value: int
    icon:  str
    color: int


    def __str__(self):
        return self.icon



class Rarity(Enum):
    P = PERK     = Tier(-1, '🟡', 0xFFFF33)
    C = COMMON    = Tier(0, '⚪', 0xB1B1B1)
    R = RARE      = Tier(1, '🔵', 0x55ACEE)
    E = EPIC      = Tier(2, '🟣', 0xCC41CC)
    L = LEGENDARY = Tier(3, '🟠', 0xE0A23C)
    M = MYTHICAL  = Tier(4, '🟤', 0xFE6333)
    D = DIVINE    = Tier(5, '⚪', 0xFFFFFF)



class Mech:
    def __init__(self):
        self.mass = 0
        self.torso = None
        self.legs = None
        self.drone = None
        self.weapons = {
            'top_right': None,
            'top_left': None,
            'side_right_upper': None,
            'side_right_lower': None,
            'side_left_upper': None,
            'side_left_lower': None}
        self.specials = {
            'tele': None,
            'charge': None,
            'hook': None}
        self.modules = [None] * 8


    def display(self) -> str:
        return ''


    @property
    def weight(self):
        # may have to calculate
        return self.mass



class _StatMissing:
    """Represents a missing stat"""
    pass



def validate_stat(stat: str, value: Any=None, none_passes: bool=True, *, obj: object=AnyStats) -> bool:
    if stat not in obj.__annotations__:
        return False

    if value is None:
        return True

    args = None
    valid = obj.__annotations__[stat]
    if isinstance(valid, GenericAlias):
        args = get_args(valid)
        valid = valid.__origin__

    if not isinstance(value, valid):
        return False

    if args is None:
        return True

    if not isinstance(value, Iterable):
        return False

    for arg, val in zip_longest(args, value, fillvalue=_StatMissing):
        if arg is _StatMissing or val is _StatMissing:
            return False

        if val is None:
            if not none_passes:
                return False

        elif not isinstance(val, arg):
            return False

    else:
        return True



@dataclass
class PhyDamageMixin:
    phyDmg:    tuple[int, int] | None = None
    phyResDmg: int | None = None


@dataclass
class EleDamageMixin:
    eleDmg:    tuple[int, int] | None = None
    eneDmg:    int | None = None
    eneCapDmg: int | None = None
    eneRegDmg: int | None = None
    eleResDmg: int | None = None

@dataclass
class ExpDamageMixin:
    expDmg:    tuple[int, int] | None = None
    heaDmg:    int | None = None
    heaCapDmg: int | None = None
    heaColDmg: int | None = None
    expResDmg: int | None = None



@dataclass
class ModuleMixin:
    health: int | None
    eneCap: int | None
    eneReg: int | None
    heaCap: int | None
    heaCol: int | None
    bulletCap: int | None
    rocketCap: int | None
    phyRes: int | None
    expRes: int | None
    eleRes: int | None



@dataclass
class Item:
    weight: int
    rarity: Rarity | tuple[Rarity, Rarity]
    image: str | None


    @classmethod
    def from_dict(cls, _dict: dict[str, Any]) -> Item:
        weight = _dict.get('weight')
        rarity = _dict.get('rarity')
        image  = _dict.get('image')

        if weight is None or rarity is None:
            raise TypeError('weight/rarity not found in the dict')

        if image is not None and not isinstance(image, str):
            raise TypeError('image has to be a url string')

        if validate_stat('weight', weight, obj=cls) and validate_stat('rarity', rarity, obj=cls):
            return cls(weight, rarity, image)

        raise TypeError('')



@dataclass
class Torso(Item):
    health: int
    eneCap: int
    eneReg: int
    heaCap: int
    heaCol: int
    bulletCap: int | None
    rocketCap: int | None
    phyRes: int = 0
    expRes: int = 0
    eleRes: int = 0



@dataclass
class LegBase:
    health: int
    phyRes: int
    expRes: int
    eleRes: int
    walk: int
    jump: int | None = None
    range: tuple[int, int] = (1, 1)
    push: int = 1
    uses: int | None = None



@dataclass
class Legs(PhyDamageMixin, EleDamageMixin, ExpDamageMixin, LegBase, Item):
    pass

# , PhyDamageMixin, EleDamageMixin, ExpDamageMixin
