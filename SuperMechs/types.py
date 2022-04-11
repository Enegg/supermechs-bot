from __future__ import annotations

import typing as t

from typing_extensions import NotRequired

AnyType = t.Literal["TORSO", "LEGS", "DRONE", "SIDE_WEAPON", "TOP_WEAPON", "TELE", "CHARGE", "HOOK", "MODULE"]
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
    image: str
    width:  NotRequired[int]
    height: NotRequired[int]
    type: AnyType
    element: AnyElement
    transform_range: str
    stats:  AnyStats
    divine: NotRequired[AnyStats]
    tags: NotRequired[list[str]]


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
