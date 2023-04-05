from __future__ import annotations

import logging
import typing as t

from attrs import define, field
from attrs.validators import max_len

from .core import StringLimits, abbreviate_names, sanitize_name
from .item import Item
from .typedefs import ID, AnyItemPack, Name

__all__ = ("ItemPack", "extract_info")

LOGGER = logging.getLogger(__name__)


class PackConfig(t.NamedTuple):
    version: str
    key: str
    name: str
    description: str


def extract_info(pack: AnyItemPack) -> PackConfig:
    """Extract version, key, name and description of the pack.

    Raises
    ------
    TypeError on unknown version.
    """
    if "version" not in pack or pack["version"] == "1":
        config = pack["config"]
        version = "1"

    elif pack["version"] in ("2", "3"):
        config = pack
        version = pack["version"]

    else:
        raise TypeError(f"Unknown pack version: {pack['version']!r}")

    if (name := pack.get("name")) is None:
        name = "<no name>"

    else:
        name = sanitize_name(name)

    if (description := pack.get("description")) is None:
        description = "<no description>"

    else:
        description = sanitize_name(description, StringLimits.description)

    return PackConfig(version, config["key"], name, description)


@define
class ItemPack:
    """Object representing an item pack."""

    key: str = field(validator=max_len(20))
    name: str = field(default="<no name>", validator=max_len(StringLimits.name))
    description: str = field(
        default="<no description>", validator=max_len(StringLimits.description)
    )
    # personal packs
    custom: bool = False

    # Item ID to Item
    items: dict[ID, Item] = field(
        factory=dict, init=False, repr=lambda items: f"{{<{len(items)} items>}}"
    )
    # Item name to item ID
    names_to_ids: dict[Name, ID] = field(factory=dict, init=False, repr=False)
    # Abbrev to a set of names the abbrev matches
    name_abbrevs: dict[str, set[Name]] = field(factory=dict, init=False, repr=False)

    def __contains__(self, value: Name | ID | Item) -> bool:
        if isinstance(value, str):
            return value in self.names_to_ids

        if isinstance(value, int):
            return value in self.items

        if isinstance(value, Item):
            return value.pack_key == self.key and value.id in self.items

        return NotImplemented

    def load(self, pack: AnyItemPack, /) -> None:
        """Load pack items from data."""

        for item_dict in pack["items"]:
            item = Item.from_json(item_dict, self.key, self.custom)
            self.items[item.id] = item
            self.names_to_ids[item.name] = item.id

        self.name_abbrevs |= abbreviate_names(self.names_to_ids)

    def get_item_by_name(self, name: Name) -> Item:
        try:
            id = self.names_to_ids[name]
            return self.items[id]

        except KeyError as err:
            err.args = (f"No item named {name!r} in the pack",)
            raise

    def get_item_by_id(self, item_id: ID) -> Item:
        try:
            return self.items[item_id]

        except KeyError as err:
            err.args = (f"No item with id {item_id} in the pack",)
            raise

    def iter_item_names(self) -> t.Iterator[Name]:
        return iter(self.names_to_ids)
