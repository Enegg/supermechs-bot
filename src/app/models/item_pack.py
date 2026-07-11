from collections import abc

import attrs

from app.class_utils import limited_repr

import supermechs.all as sm

__all__ = ("ItemPack",)


@attrs.frozen(kw_only=True)
class ItemPack:
    """Mapping-like container of items."""

    reloaded_items: abc.Mapping[sm.Item.Id, sm.Item] = attrs.field(factory=dict, repr=limited_repr)
    legacy_items: abc.Mapping[sm.Item.Id, sm.Item] = attrs.field(factory=dict, repr=limited_repr)
    hidden_items: abc.Mapping[sm.Item.Id, sm.Item] = attrs.field(factory=dict, repr=limited_repr)
