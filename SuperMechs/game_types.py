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


class AnyStats(t.TypedDict, total=False):
    # stats sorted in order they appear in-game
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
    walk: int
    jump: int
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
    bulletCost: int
    rocketCost: int


class Attachment(t.TypedDict):
    x: int
    y: int


Attachments = dict[str, Attachment]
AttachmentType = t.TypeVar("AttachmentType", Attachment, Attachments, None)


class ItemDictBase(t.TypedDict):
    id: int
    name: str
    image: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]
    type: AnyType
    element: AnyElement
    transform_range: str
    stats: AnyStats
    tags: NotRequired[list[t.Literal["sword", "melee", "roller"]]]


class ItemDictAttachment(ItemDictBase):
    attachment: Attachment


class ItemDictAttachments(ItemDictBase):
    attachment: Attachments


ItemDict = ItemDictBase | ItemDictAttachment | ItemDictAttachments


class PackConfig(t.TypedDict):
    key: str
    name: str
    base_url: str
    description: str


class ItemPack(t.TypedDict):
    config: PackConfig
    items: list[ItemDict]


class SpritePosition(t.TypedDict):
    width: int
    height: int
    x: int
    y: int


class ItemPackv2(t.TypedDict):
    version: str
    key: str
    name: str
    description: str
    spritesSheet: str
    spritesMap: dict[str, SpritePosition]
    items: list[ItemDict]


class TagsDict(t.TypedDict):
    premium: bool
    sword: bool
    melee: bool
    roller: bool
    legacy: bool
    require_jump: bool
    custom: bool


class ItemSerialized(t.TypedDict):
    slotName: str
    id: int
    name: str
    type: str
    stats: AnyStats
    tags: TagsDict
    element: str
    timesUsed: t.Literal[0]


class MechSerialized(t.TypedDict):
    name: str
    setup: list[int]


class WUSerialized(t.TypedDict):
    name: str
    itemsHash: str
    mech: MechSerialized
