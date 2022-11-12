import typing as t

from typing_extensions import NotRequired

from .game_types import AnyStats, LiteralElement, LiteralType, RawAttachment, RawAttachments


class TiersMixin(t.TypedDict, total=False):
    common: AnyStats
    max_common: AnyStats
    rare: AnyStats
    max_rare: AnyStats
    epic: AnyStats
    max_epic: AnyStats
    legendary: AnyStats
    max_legendary: AnyStats
    mythical: AnyStats
    max_mythical: AnyStats
    divine: AnyStats


class SpritePosition(t.TypedDict):
    width: int
    height: int
    x: int
    y: int


class SpritesSheetMixin(t.TypedDict):
    spritesSheet: str
    spritesMap: dict[str, SpritePosition]


class ItemDictBase(t.TypedDict):
    id: int
    name: str
    type: LiteralType
    element: LiteralElement
    transform_range: str
    tags: NotRequired[list[t.Literal["sword", "melee", "roller"]]]
    width: NotRequired[int]
    height: NotRequired[int]
    attachment: NotRequired[RawAttachment | RawAttachments]


# -------------------------------------- v1 --------------------------------------
# https://gist.githubusercontent.com/ctrlraul/3b5669e4246bc2d7dc669d484db89062/raw
# "version": "1" or non-existent
# "config" with "base_url"
# "image" per item (usually name without spaces + .png)


class ItemDictVer1(ItemDictBase):
    stats: AnyStats
    image: str


class PackConfig(t.TypedDict):
    key: str
    name: str
    description: str
    base_url: str


class ItemPackVer1(t.TypedDict):
    version: NotRequired[t.Literal["1"]]
    config: PackConfig
    items: list[ItemDictVer1]


# -------------------------------------- v2 --------------------------------------
# https://gist.githubusercontent.com/ctrlraul/22b71089a0dd7fef81e759dfb3dda67b/raw
# "version": "2"
# no "config"
# spritesheets


class ItemDictVer2(ItemDictBase):
    stats: AnyStats


class ItemPackVer2(SpritesSheetMixin):
    version: t.Literal["2"]
    key: str
    name: str
    description: str
    items: list[ItemDictVer2]


# -------------------------------------- v3 --------------------------------------
# https://raw.githubusercontent.com/Enegg/Item-packs/master/items.json
# "version": "3" or "standalone"
# lacks tags and attachments


class ItemDictVer3(ItemDictBase, TiersMixin):
    pass


class ItemPackVer3(SpritesSheetMixin):
    version: t.Literal["3"]
    key: str
    name: str
    description: str
    items: list[ItemDictVer3]


AnyItemDict = ItemDictVer1 | ItemDictVer2 | ItemDictVer3
AnyItemPack = ItemPackVer1 | ItemPackVer2 | ItemPackVer3
