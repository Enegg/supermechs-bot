from __future__ import annotations

import typing as t

from typing_extensions import NotRequired

AnyType = t.Literal[
    "TORSO",
    "LEGS",
    "DRONE",
    "SIDE_WEAPON",
    "TOP_WEAPON",
    "TELEPORTER",
    "CHARGE_ENGINE",
    "GRAPPLING_HOOK",
    "MODULE",
]
AnyElement = t.Literal["PHYSICAL", "EXPLOSIVE", "ELECTRIC", "COMBINED"]

# fmt: off
AnyMechStatKey = t.Literal[
    "weight", "health",
    "eneCap", "eneReg",
    "heaCap", "heaCol",
    "phyRes", "expRes", "eleRes",
    "bulletsCap", "rocketsCap",
    "walk", "jump"
]

AnyStatKey = AnyMechStatKey | t.Literal[
    "phyDmg", "phyResDmg",
    "expDmg", "heaDmg", "heaCapDmg", "heaColDmg", "expResDmg",
    "eleDmg", "eneDmg", "eneCapDmg", "eneRegDmg", "eleResDmg",
    "range",
    "push", "pull", "recoil", "retreat", "advance",
    "uses",
    "backfire", "heaCost", "eneCost", "bulletsCost", "rocketsCost"
]
# fmt: on


class StatName(t.TypedDict):
    default: str
    in_game: NotRequired[str]
    short: NotRequired[str]


class StatDict(t.TypedDict):
    names: StatName
    emoji: NotRequired[str]
    beneficial: NotRequired[t.Literal[False]]
    buff: NotRequired[t.Literal["+", "+%", "-%", "+2%"]]


class AnyMechStats(t.TypedDict, total=False):
    weight: int
    health: int
    eneCap: int
    eneReg: int
    heaCap: int
    heaCol: int
    phyRes: int
    expRes: int
    eleRes: int
    bulletsCap: int
    rocketsCap: int
    walk: int
    jump: int


class AnyStats(AnyMechStats, total=False):
    # stats sorted in order they appear in-game
    phyDmg: list[int]
    phyResDmg: int
    eleDmg: list[int]
    eneDmg: int
    eneCapDmg: int
    eneRegDmg: int
    eleResDmg: int
    expDmg: list[int]
    heaDmg: int
    heaCapDmg: int
    heaColDmg: int
    expResDmg: int
    # walk, jump
    range: list[int]
    push: int
    pull: int
    recoil: int
    advance: int
    retreat: int
    uses: int
    backfire: int
    heaCost: int
    eneCost: int
    bulletsCost: int
    rocketsCost: int


class Attachment(t.TypedDict):
    x: int
    y: int


# These may make sense to be somewhere else
Attachments = dict[str, Attachment]
AnyAttachment = Attachment | Attachments | None
AttachmentType = t.TypeVar("AttachmentType", bound=AnyAttachment)
