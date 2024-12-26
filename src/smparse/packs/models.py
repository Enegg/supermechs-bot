from collections import abc
from typing import Literal, TypeAlias

import attrs
import attrs.validators as v
from monads.option import Null, Option

from supermechs.all import ItemStats

LiteralType: TypeAlias = Literal[
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
LiteralElement: TypeAlias = Literal["PHYSICAL", "EXPLOSIVE", "ELECTRIC", "COMBINED"]


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
    stats: ItemStats = attrs.field(factory=ItemStats)


@attrs.define(kw_only=True)
class ItemPackV1:
    config: PackBase
    items: abc.Sequence[ItemV1]


# ------------------------------------------- version 2 --------------------------------------------
ItemV2: TypeAlias = ItemV1


@attrs.define(kw_only=True)
class ItemPackV2(PackBase):
    items: abc.Sequence[ItemV2]


# ------------------------------------------- version 3 --------------------------------------------
@attrs.define(kw_only=True)
class ItemV3(ItemBase):
    # fmt: off
    common:        ItemStats | None = None
    max_common:    ItemStats | None = None
    rare:          ItemStats | None = None
    max_rare:      ItemStats | None = None
    epic:          ItemStats | None = None
    max_epic:      ItemStats | None = None
    legendary:     ItemStats | None = None
    max_legendary: ItemStats | None = None
    mythical:      ItemStats | None = None
    max_mythical:  ItemStats | None = None
    divine:        ItemStats | None = None
    # fmt: on


@attrs.define(kw_only=True)
class ItemPackV3(PackBase):
    items: abc.Sequence[ItemV3]


AnyItemPack: TypeAlias = ItemPackV1 | ItemPackV2 | ItemPackV3
