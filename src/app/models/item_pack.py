from collections import abc
from typing import NamedTuple

import attrs
from monads.option import Null, Option

from app.class_utils import limited_repr

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

    reloaded_items: abc.Mapping[sm.Item.Id, sm.Item] = attrs.field(factory=dict, repr=limited_repr)
    legacy_items: abc.Mapping[sm.Item.Id, sm.Item] = attrs.field(factory=dict, repr=limited_repr)
    hidden_items: abc.Mapping[sm.Item.Id, sm.Item] = attrs.field(factory=dict, repr=limited_repr)
