from collections import abc
from typing import TypeAlias

import attrs
import attrs.validators as v

from app.models.graphics import Joints


@attrs.define(kw_only=True)
class ItemGfx:
    id: int = attrs.field(validator=v.gt(0))
    width: int = 0
    height: int = 0
    joints: Joints = Joints.ZERO


# -------------------------------------------- per-item --------------------------------------------
@attrs.define(kw_only=True)
class PackBase:
    key: str
    base_url: str


@attrs.define(kw_only=True)
class ItemGraphicsV1(ItemGfx):
    image: str


@attrs.define(kw_only=True)
class ItemPackGfx:
    config: PackBase
    items: abc.Sequence[ItemGfx]


# ----------------------------------------- sprites sheet ------------------------------------------
@attrs.define
class Rectangle:
    x: int
    y: int
    width: int
    height: int


@attrs.define(kw_only=True)
class SpritesSheetGfx:
    key: str
    sprites_url: str
    sprites_map: abc.Mapping[str, Rectangle]
    items: abc.Sequence[ItemGfx]


AnyGfx: TypeAlias = ItemPackGfx | SpritesSheetGfx
