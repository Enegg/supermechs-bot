from __future__ import annotations

import asyncio
import json
import logging
import typing as t
from io import TextIOBase
from pathlib import Path

from attrs import define, field

from abstract.files import URL, Resource, Urlish
from shared import SESSION_CTX

from .core import abbreviate_names
from .images import AttachedImage
from .item import AnyItem, Item
from .typedefs.pack_versioning import AnyItemPack, ItemPackVer1, ItemPackVer2
from .utils import MISSING, js_format

__all__ = ("PackInterface",)

logger = logging.getLogger(__name__)


def load_json(fp: str | Path | TextIOBase, /) -> t.Any:
    """Load data from local file."""

    logger.info(f"Loading from file {fp}")

    match fp:
        case str() | Path():
            with open(fp) as file:
                return json.load(file)

        case TextIOBase():
            return json.load(fp)

        case _:
            raise TypeError("Unsuppored file type")


async def fetch_json(url: Urlish, /) -> t.Any:
    """Loads a json from url."""

    logger.info(f"Fetching from url {url}")

    async with SESSION_CTX.get().get(url) as response:
        response.raise_for_status()
        return await response.json(encoding="utf-8", content_type=None)


HandleRet = tuple[t.Iterator[AnyItem], list[asyncio.Task[None]]]


async def pack_v1_handle(pack: ItemPackVer1, custom: bool = False) -> HandleRet:
    base_url = pack["config"]["base_url"]

    tasks: list[asyncio.Task[None]] = []

    def loop():
        for item_dict in pack["items"]:
            item = Item.from_json(item_dict, custom, MISSING, None)

            url = js_format(item_dict["image"], url=base_url)
            task = asyncio.create_task(item.image.with_resource(URL(url)))
            tasks.append(task)
            yield item

    return loop(), tasks


async def pack_v2_handle(pack: ItemPackVer2, custom: bool = False) -> HandleRet:
    sprite_map = pack["spritesMap"]

    from PIL.Image import open

    base_image = open(await URL(pack["spritesSheet"]).open())

    def loop():
        for item_dict in pack["items"]:
            key = item_dict["name"].replace(" ", "")
            item = Item.from_json(item_dict, custom, base_image, sprite_map[key])
            yield item

    return loop(), []


@define
class PackInterface:
    key: str = MISSING
    name: str = MISSING
    description: str = MISSING
    # Item ID to Item
    items: dict[int, AnyItem] = field(
        factory=dict, init=False, repr=lambda s: f"{{... {len(s)} items}}"
    )
    # Item name to item ID
    names_to_ids: dict[str, int] = field(factory=dict, init=False, repr=False)
    name_abbrevs: dict[str, set[str]] = field(factory=dict, init=False, repr=False)

    # personal packs
    custom: bool = False

    def __contains__(self, value: str | int | AnyItem) -> bool:
        match value:
            case str() as name:
                return name in self.names_to_ids

            case int() as id:
                return id in self.items

            case Item() as item:
                return item.id in self.items

            case _:
                return NotImplemented

    async def load(self, resource: Resource[t.Any], /, **extra: t.Any) -> None:
        """Load the item pack from a resource."""

        # TODO: split the logic in this method into functions

        pack: AnyItemPack = await resource.json()
        pack |= extra  # type: ignore

        self.extract_info(pack)
        logger.info(f"Pack {self.name!r} extracted; key: {self.key!r}")

        if "version" not in pack or pack["version"] == "1":
            handle = pack_v1_handle(pack, self.custom)

        elif pack["version"] == "2":
            handle = pack_v2_handle(pack, self.custom)

        elif pack["version"] == "3":
            return

        else:
            logger.info("Pack version not recognized")
            return

        iterator, tasks = await handle

        for item in iterator:
            self.items[item.id] = item
            self.names_to_ids[item.name] = item.id

        # logger.warning(f"Item {item.name!r} failed to load image")

        self.name_abbrevs = abbreviate_names(self.names_to_ids)

        if tasks:
            await asyncio.wait(tasks, timeout=5, return_when="ALL_COMPLETED")

        # TODO: this may be eligible to run in an executor
        for funcs in AttachedImage._postprocess.values():
            for func in funcs:
                func()

        AttachedImage.clear_cache()
        logger.info("Item images loaded")

    def get_item_by_name(self, name: str) -> AnyItem:
        try:
            id = self.names_to_ids[name]
            return self.items[id]

        except KeyError as err:
            err.args = (f"No item with name {name!r} in the pack",)
            raise

    def get_item_by_id(self, item_id: int) -> AnyItem:
        try:
            return self.items[item_id]

        except KeyError as err:
            err.args = (f"No item with id {item_id} in the pack",)
            raise

    def iter_item_names(self) -> t.Iterator[str]:
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
