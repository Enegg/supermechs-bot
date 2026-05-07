from collections import abc
from typing import Literal

import msgspec

from .common import ItemStatsDto, LiteralElement, LiteralSlot, Name, PosInt, TransformRange


class ConfigDto(msgspec.Struct, kw_only=True):
    base_url: str | msgspec.UnsetType = msgspec.UNSET
    key: str | msgspec.UnsetType = msgspec.UNSET
    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET


class ItemDto(msgspec.Struct, kw_only=True):
    id: PosInt
    image: str | msgspec.UnsetType = msgspec.UNSET
    name: Name
    slot_id: LiteralSlot = msgspec.field(name="type")
    element: LiteralElement = "OTHER"
    transform_range: TransformRange = "C"
    stats: ItemStatsDto
    # attachment
    tags: abc.Sequence[str] = ()


class ItemPackDto(msgspec.Struct, kw_only=True, tag_field="version", tag="1"):
    config: ConfigDto | msgspec.UnsetType = msgspec.UNSET
    key: str | msgspec.UnsetType = msgspec.UNSET
    name: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    base_url: str | msgspec.UnsetType = msgspec.UNSET
    sprite_handling_method: Literal["individual"] = "individual"
    legacy: bool = False
    items: abc.Sequence[ItemDto]
