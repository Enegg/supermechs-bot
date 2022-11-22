from __future__ import annotations

import asyncio
import logging
import typing as t

from attrs import define, field

from abstract.files import URL, Resource

from .core import abbreviate_names
from .images import AttachedImage, parse_raw_attachment
from .item import AnyItem, Item
from .typedefs import ID, AnyItemPack, ItemPackVer1, ItemPackVer2, ItemPackVer3, Name
from .utils import MISSING, js_format

__all__ = ("PackInterface",)

LOGGER = logging.getLogger(__name__)

HandleRet = tuple[t.Iterator[AnyItem], set[t.Awaitable[None]]]


async def pack_v1_handle(pack: ItemPackVer1, custom: bool = False) -> HandleRet:
    cfg = pack["config"]
    pack_key = cfg["key"]
    base_url = cfg["base_url"]

    tasks: set[t.Awaitable[None]] = set()

    def loop():
        for item_dict in pack["items"]:
            resource = URL(js_format(item_dict["image"], url=base_url))
            attachment = parse_raw_attachment(item_dict.get("attachment", None))
            renderer, task = AttachedImage.from_resource(resource, attachment)
            tasks.add(task)

            yield Item.from_json(item_dict, pack_key, custom, renderer)

    return loop(), tasks


async def pack_v2_handle(pack: ItemPackVer2, custom: bool = False) -> HandleRet:
    sprite_map = pack["spritesMap"]
    key = pack["key"]

    from PIL.Image import open

    base_image = open(await URL(pack["spritesSheet"]).open())

    def loop():
        for item_dict in pack["items"]:
            attachment = parse_raw_attachment(item_dict.get("attachment", None))
            renderer = AttachedImage(base_image, attachment)
            sprite_key = item_dict["name"].replace(" ", "")

            renderer.crop(sprite_map[sprite_key])
            item = Item.from_json(item_dict, key, custom, renderer)
            yield item

    return loop(), set()


async def pack_v3_handle(pack: ItemPackVer3, custom: bool = False) -> HandleRet:
    # TODO
    raise NotImplementedError


@define
class PackInterface:
    key: str = MISSING
    name: str = MISSING
    description: str = MISSING
    # Item ID to Item
    items: dict[ID, AnyItem] = field(
        factory=dict, init=False, repr=lambda s: f"{{... {len(s)} items}}"
    )
    # Item name to item ID
    names_to_ids: dict[Name, ID] = field(factory=dict, init=False, repr=False)
    # Abbrev to a set of names the abbrev matches
    name_abbrevs: dict[str, set[Name]] = field(factory=dict, init=False, repr=False)

    # personal packs
    custom: bool = False

    def __contains__(self, value: str | int | AnyItem) -> bool:
        if isinstance(value, str):
            return value in self.names_to_ids

        if isinstance(value, int):
            return value in self.items

        if isinstance(value, Item):
            return value.id in self.items

        return NotImplemented

    async def load(self, resource: Resource, /, **extra: t.Any) -> None:
        """Load the item pack from a resource."""

        # TODO: split the logic in this method into functions

        pack: AnyItemPack = await resource.json()
        pack |= extra  # type: ignore

        self.extract_info(pack)

        if "version" not in pack or pack["version"] == "1":
            handle = pack_v1_handle(pack, self.custom)

        elif pack["version"] == "2":
            handle = pack_v2_handle(pack, self.custom)

        elif pack["version"] == "3":
            handle = pack_v3_handle(pack, self.custom)

        else:
            raise TypeError(f"Unknown pack version: {pack['version']!r}")

        iterator, tasks = await handle

        for item in iterator:
            self.items[item.id] = item
            self.names_to_ids[item.name] = item.id

        self.name_abbrevs |= abbreviate_names(self.names_to_ids)

        if tasks:
            await asyncio.wait(tasks, timeout=5, return_when="ALL_COMPLETED")

        # TODO: this may be eligible to run in an executor
        for funcs in AttachedImage._postprocess.values():
            for func in funcs:
                func()

        AttachedImage._clear_cache()
        LOGGER.info("Item images loaded")

    def get_item_by_name(self, name: Name) -> AnyItem:
        try:
            id = self.names_to_ids[name]
            return self.items[id]

        except KeyError as err:
            err.args = (f"No item with name {name!r} in the pack",)
            raise

    def get_item_by_id(self, item_id: ID) -> AnyItem:
        try:
            return self.items[item_id]

        except KeyError as err:
            err.args = (f"No item with id {item_id} in the pack",)
            raise

    def iter_item_names(self) -> t.Iterator[Name]:
        return iter(self.names_to_ids)

    def extract_info(self, pack: AnyItemPack) -> None:
        """Extract key, name and description of the pack."""

        if "version" not in pack or pack["version"] == "1":
            config = pack["config"]

        else:
            config = pack

        self.key = config["key"]
        self.name = config["name"]
        self.description = config["description"]
        LOGGER.info(f"Pack {self.name!r} extracted; key: {self.key!r}")
