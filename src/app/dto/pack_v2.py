from collections import abc
from typing import Literal

import msgspec

from .common import (
    ItemStatsDto,
    LiteralElement,
    LiteralType,
    MixedJointsDto,
    Name,
    PosInt,
    TransformRange,
    UInt,
)


class SpriteRectDto(msgspec.Struct):
    width: PosInt
    height: PosInt
    x: UInt
    y: UInt


class ConfigDto(msgspec.Struct, kw_only=True):
    key: str | msgspec.UnsetType = msgspec.UNSET
    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET


class ItemDto(msgspec.Struct, kw_only=True):
    id: PosInt
    name: Name
    type: LiteralType
    width: UInt = 0
    height: UInt = 0
    element: LiteralElement = "OTHER"
    transform_range: TransformRange = "C"
    stats: ItemStatsDto
    attachment: MixedJointsDto | msgspec.UnsetType = msgspec.UNSET
    tags: abc.Sequence[str] = ()


class ItemPackDto(msgspec.Struct, kw_only=True, tag_field="version", tag="2"):
    config: ConfigDto | msgspec.UnsetType = msgspec.UNSET
    key: str | msgspec.UnsetType = msgspec.UNSET
    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    sprite_sheet_url: str = msgspec.field(name="spritesSheet")
    sprite_map: abc.Mapping[str, SpriteRectDto] = msgspec.field(name="spritesMap")
    sprite_handling_method: Literal["spritessheet"] = "spritessheet"
    legacy: bool = False
    items: abc.Sequence[ItemDto]
