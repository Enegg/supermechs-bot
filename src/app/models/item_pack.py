from collections import abc
from typing import NamedTuple

import attrs
from monads.option import Null, Option

from app import snowflake
from app.class_utils import limited_repr
from app.models.ids import PackId

import dupermechs.all as sm

__all__ = ("ItemPack",)


class ItemPackMetadata(NamedTuple):
    version: str = "1"
    key: Option[str] = Null.null
    name: Option[str] = Null.null
    description: Option[str] = Null.null


@attrs.frozen(kw_only=True)
class ItemPack:
    """Mapping-like container of items."""

    id: PackId = attrs.field(factory=snowflake.new[PackId])
    reloaded_items: abc.Mapping[sm.Item.Id, sm.IItem] = attrs.field(factory=dict, repr=limited_repr)
    legacy_items: abc.Mapping[sm.Item.Id, sm.IItem] = attrs.field(factory=dict, repr=limited_repr)
    hidden_items: abc.Mapping[sm.Item.Id, sm.IItem] = attrs.field(factory=dict, repr=limited_repr)
