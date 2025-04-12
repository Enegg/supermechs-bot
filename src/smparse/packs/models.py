from collections import abc
from typing import Literal

import attrs
import attrs.validators as v
from monads.option import Null, Option

import supermechs.all as sm

type LiteralType = Literal[
    "TORSO",
    "LEGS",
    "DRONE",
    "SIDE_WEAPON",
    "TOP_WEAPON",
    "TELEPORTER",
    "CHARGE_ENGINE",
    "CHARGE",
    "GRAPPLING_HOOK",
    "HOOK",
    "MODULE",
]
type LiteralElement = Literal["PHYSICAL", "EXPLOSIVE", "ELECTRIC", "COMBINED"]


@attrs.define(kw_only=True)
class ItemBase:
    id: int = attrs.field(validator=v.gt(0))
    name: Option[str] = Null.null
    type: Option[LiteralType] = Null.null
    element: Option[LiteralElement] = Null.null
    transform_range: str = "C-C"
    tags: abc.Set[str] = frozenset()


@attrs.define(kw_only=True)
class PackBase:
    key: str
    name: Option[str] = Null.null
    description: Option[str] = Null.null


# ------------------------------------------- version 1 --------------------------------------------
@attrs.define(kw_only=True)
class ItemV1(ItemBase):
    stats: sm.ItemStats = attrs.field(factory=sm.ItemStats)


@attrs.define(kw_only=True)
class ItemPackV1:
    config: PackBase
    items: abc.Sequence[ItemV1]


# ------------------------------------------- version 2 --------------------------------------------
type ItemV2 = ItemV1


@attrs.define(kw_only=True)
class ItemPackV2(PackBase):
    items: abc.Sequence[ItemV2]


# ------------------------------------------- version 3 --------------------------------------------
@attrs.define(kw_only=True)
class ItemV3(ItemBase):
    # fmt: off
    common:        sm.ItemStats | None = None
    max_common:    sm.ItemStats | None = None
    rare:          sm.ItemStats | None = None
    max_rare:      sm.ItemStats | None = None
    epic:          sm.ItemStats | None = None
    max_epic:      sm.ItemStats | None = None
    legendary:     sm.ItemStats | None = None
    max_legendary: sm.ItemStats | None = None
    mythical:      sm.ItemStats | None = None
    max_mythical:  sm.ItemStats | None = None
    divine:        sm.ItemStats | None = None
    # fmt: on


@attrs.define(kw_only=True)
class ItemPackV3(PackBase):
    items: abc.Sequence[ItemV3]


type AnyItemPack = ItemPackV1 | ItemPackV2 | ItemPackV3
