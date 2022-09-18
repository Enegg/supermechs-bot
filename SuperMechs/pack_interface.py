from __future__ import annotations

import asyncio
import json
import logging
import typing as t
from functools import partial
from io import TextIOBase
from pathlib import Path

from attrs import define, field
from SuperMechs.core import abbreviate_names

from shared import SESSION_CTX

from .enums import Type
from .game_types import AnyAttachment
from .images import AttachedImage, create_synthetic_attachment, fetch_image_bytes
from .item import AnyItem, Item
from .pack_versioning import AnyItemPack, ItemPackVer1
from .utils import MISSING, js_format

if t.TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL

__all__ = ("PackInterface",)

logger = logging.getLogger(f"SuperMechs.{__name__}")


def pathify(maybe_path: StrOrURL | Path) -> StrOrURL | Path:
    if isinstance(maybe_path, str) and (path := Path(maybe_path)).is_file():
        return path

    return maybe_path


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


async def fetch_json(url: StrOrURL, /) -> t.Any:
    """Loads a json from url."""

    logger.info(f"Fetching from url {url}")

    async with SESSION_CTX.get().get(url) as response:
        response.raise_for_status()
        return await response.json(encoding="utf-8", content_type=None)


def assert_attachment_set(type: Type, image: AttachedImage[AnyAttachment]) -> None:
    if type.attachable and image.attachment is None:
        image.attachment = create_synthetic_attachment(image, type)


def pack_v1_handle(pack: ItemPackVer1):
    base_url = pack["config"]["base_url"]

    def item_iterator():
        for item_dict in pack["items"]:
            width = item_dict.get("width", 0)
            height = item_dict.get("height", 0)
            renderer = AttachedImage(attachment=item_dict.get("attachment", None))
            image_url = js_format(item_dict["image"], url=base_url)

            yield item_dict, renderer

    return item_iterator


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
    names_to_ids: dict[str, int] = field(factory=dict, init=False)
    name_abbrevs: dict[str, set[str]] = field(factory=dict, init=False)

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

    @staticmethod
    async def fetch_pack(pack_link: StrOrURL | Path, /, **extra: t.Any) -> AnyItemPack:
        """Loads items pack, parses items, and then fetches images."""
        match pathify(pack_link):
            case Path() as path:
                pack: AnyItemPack = load_json(path)

            case url:
                pack: AnyItemPack = await fetch_json(url)

        pack |= extra  # type: ignore
        return pack

    async def load(self, pack_link: StrOrURL | Path, /, **extra: t.Any) -> None:
        """Do all the tasks it takes to load an item pack: fetch item pack, load items, load images"""

        # TODO: split the logic in this method into functions

        pack = await self.fetch_pack(pack_link, **extra)
        self.extract_info(pack)
        logger.info(f"Pack {self.name!r} extracted; key: {self.key!r}")

        promises: list[tuple[AttachedImage, t.Any, t.Callable[[AttachedImage], None]]] = []

        if "version" not in pack or pack["version"] == "1":
            base_url = pack["config"]["base_url"]
            item_dicts_list = pack["items"]

            get_promise = lambda item_dict: js_format(item_dict["image"], url=base_url)
            spritesheet_url = None

        else:
            item_dicts_list = pack["items"]
            sprite_map = pack["spritesMap"]
            spritesheet_url = pack["spritesSheet"]

            get_promise = lambda item_dict: sprite_map[item_dict["name"].replace(" ", "")]

        for item_dict in item_dicts_list:
            renderer = AttachedImage(attachment=item_dict.get("attachment", None))
            width = item_dict.get("width", 0)
            height = item_dict.get("height", 0)

            def resize_later():
                image = renderer.image
                w = width or image.width
                h = height or image.height
                renderer.image = image.resize((w, h))

            item = Item.from_json(item_dict, renderer, self.custom)
            self.items[item.id] = item
            self.names_to_ids[item.name] = item.id

            try:
                promises.append(
                    (renderer, get_promise(item_dict), partial(assert_attachment_set, item.type))
                )

            except (KeyError, TypeError):
                logger.warning(f"Item {item.name!r} failed to load image")

        self.name_abbrevs = abbreviate_names(self.names_to_ids)

        if spritesheet_url is not None:
            from PIL.Image import open

            spritesheet = open(await fetch_image_bytes(spritesheet_url))
            for renderer, promise, asserter in promises:
                renderer.load_image((spritesheet, promise))
                asserter(renderer)

        else:
            coros = set()

            for renderer, promise, asserter in promises:
                task = asyncio.create_task(fetch_image_bytes(promise))

                def cb(task: asyncio.Task):
                    renderer.load_image(task.result())
                    asserter(renderer)

                task.add_done_callback(cb)
                coros.add(task)

            await asyncio.wait(coros, timeout=5, return_when="ALL_COMPLETED")
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


if __name__ == "__main__":
    link = "https://gist.githubusercontent.com/ctrlraul/22b71089a0dd7fef81e759dfb3dda67b/raw"

    async def runner(link, **extra):
        from aiohttp import ClientSession

        logging.basicConfig(level="INFO")
        interface = PackInterface()
        async with ClientSession() as session:
            SESSION_CTX.set(session)
            await interface.load(link, **extra)
            return interface
