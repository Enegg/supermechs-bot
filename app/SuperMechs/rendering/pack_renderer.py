from __future__ import annotations

import asyncio
import logging
import typing as t
from functools import partial

from attrs import Factory, define, field

from files import URL, Resource
from typeshed import T, twotuple

from ..enums import Tier, Type
from ..inv_item import InvItemProto
from ..item import ItemProto
from ..pack_interface import extract_info
from ..typedefs import (
    ID,
    AnyItemDict,
    AnyItemPack,
    ItemDictVer2,
    ItemDictVer3,
    ItemPackVer1,
    ItemPackVer2,
    ItemPackVer3,
    Rectangle,
)
from ..utils import js_format
from .attachments import cast_attachment, is_attachable, parse_raw_attachment
from .sprites import ItemSprite

if t.TYPE_CHECKING:
    from PIL.Image import Image

    from ..mech import Mech

LOGGER = logging.getLogger(__name__)

LAYER_ORDER = (
    "drone",
    "side2",
    "side4",
    "top2",
    "leg2",
    "torso",
    "leg1",
    "top1",
    "side1",
    "side3",
)


class Rectangular(t.Protocol):
    """Object which has width and height."""

    @property
    def width(self) -> int:
        ...

    @property
    def height(self) -> int:
        ...


@define
class Offsets:
    """Dataclass describing how many pixels the complete image extends beyond canvas."""

    left: int = 0
    right: int = 0
    above: int = 0
    below: int = 0

    def adjust(self, image: Rectangular, x: int, y: int) -> None:
        """Updates the canvas size in-place, if the new data extends beyond previous."""
        self.left = max(self.left, -x)
        self.above = max(self.above, -y)
        self.right = max(self.right, x + image.width)
        self.below = max(self.below, y + image.height)

    def final_size(self, base_image: Rectangular) -> twotuple[int]:
        """Return the final size of the canvas, given base image."""
        return (
            self.left + max(base_image.width, self.right),
            self.above + max(base_image.height, self.below),
        )


def calculate_position(position: twotuple[int], offset: twotuple[int]) -> twotuple[int]:
    corner_x, corner_y = position
    offset_x, offset_y = offset
    return (offset_x - corner_x, offset_y - corner_y)


@define
class Canvas(t.Generic[T]):
    """Class responsible for merging layered images into one."""

    base: Image
    layers: t.Sequence[T]
    offsets: Offsets = field(factory=Offsets)
    images: list[tuple[int, int, Image] | None] = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.images = [None] * len(self.layers)

    def add_image(
        self,
        image: Image,
        layer: T,
        position: twotuple[int],
        offset: twotuple[int] = (0, 0),
    ) -> None:
        """Adds an image as a layer on the canvas."""
        # if offset is not None:
        position = calculate_position(position, offset)

        self.offsets.adjust(image, *position)
        self._put_image(image, layer, *position)

    def _put_image(self, image: Image, layer: T, x: int, y: int) -> None:
        """Place the image on the canvas."""
        self.images[self.layers.index(layer)] = (x, y, image)

    def merge(self, base_layer: T) -> Image:
        """Merges all images into one and returns it."""
        self._put_image(self.base, base_layer, 0, 0)

        from PIL.Image import new

        canvas = new(
            "RGBA",
            self.offsets.final_size(self.base),
            (0, 0, 0, 0),
        )

        for x, y, image in filter(None, self.images):
            canvas.alpha_composite(image, (x + self.offsets.left, y + self.offsets.above))

        return canvas


async def fetch_image(url: str) -> Image:
    from PIL.Image import open

    return open(await URL(url).open())


def oneshot(item_dict: AnyItemDict, image: Image, sprites: dict[ID, ItemSprite]) -> None:
    width = item_dict.get("width", image.width)
    height = item_dict.get("height", image.height)

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    if image.size != (width, height):
        image = image.resize((width, height))

    attachment = parse_raw_attachment(item_dict.get("attachment"))
    type = Type[item_dict["type"]]
    sprite = ItemSprite(image, attachment)

    if attachment is None and is_attachable(type):
        sprite._create_attachment(type)

    sprites[item_dict["id"]] = sprite


def thread_worker(funcs: t.Iterable[t.Callable[[], None]]) -> None:
    for func in funcs:
        func()


async def loader_v1(data: ItemPackVer1, sprites: dict[ID, ItemSprite]) -> None:
    pack_key = extract_info(data).key
    BASE_URL = data["config"]["base_url"]

    task_to_data: dict[asyncio.Task[Image], AnyItemDict] = {}

    for item_dict in data["items"]:
        task = asyncio.create_task(
            fetch_image(js_format(item_dict["image"], url=BASE_URL)),
            name=f"<acquire item task {pack_key} #{item_dict['id']}>",
        )
        task_to_data[task] = item_dict

    finished, _ = await asyncio.wait(task_to_data)
    sync_futures: list[t.Callable[[], None]] = []

    for task in finished:
        image = task.result()
        item_dict = task_to_data.pop(task)

        sync_futures.append(partial(oneshot, item_dict, image, sprites))

    await asyncio.to_thread(thread_worker, sync_futures)


async def loader_v2_v3(data: ItemPackVer2 | ItemPackVer3, sprites: dict[ID, ItemSprite]) -> None:
    spritessheet_url = data["spritesSheet"]
    spritessheet_map = data["spritesMap"]

    spritessheet = await fetch_image(spritessheet_url)
    sync_futures: list[t.Callable[[], None]] = []

    def sprite_creator(item_dict: ItemDictVer2 | ItemDictVer3) -> None:
        sheet_key = item_dict["name"].replace(" ", "")
        image = crop_from_spritesheet(spritessheet, spritessheet_map[sheet_key])
        oneshot(item_dict, image, sprites)

    for item_dict in data["items"]:
        sync_futures.append(partial(sprite_creator, item_dict))

    await asyncio.to_thread(thread_worker, sync_futures)


@define
class PackRenderer:
    key: str
    item_sprites: dict[ID, ItemSprite] = Factory(dict)

    async def load(self, pack: AnyItemPack) -> None:
        if "version" not in pack or pack["version"] == "1":
            await loader_v1(pack, self.item_sprites)

        elif pack["version"] == "2":
            await loader_v2_v3(pack, self.item_sprites)

        elif pack["version"] == "3":
            await loader_v2_v3(pack, self.item_sprites)

        else:
            raise ValueError(f"Unknown pack version: {pack['version']}")

        LOGGER.info(f"Pack {self.key!r} loaded {len(self.item_sprites)} sprites")

    @t.overload
    def get_item_sprite(self, item: ItemProto, /, tier: Tier) -> ItemSprite:
        ...

    @t.overload
    def get_item_sprite(self, item: InvItemProto, /) -> ItemSprite:
        ...

    def get_item_sprite(
        self, item: ItemProto | InvItemProto, /, tier: Tier | None = None
    ) -> ItemSprite:
        del tier  # TODO: implement when storing TieredSprite

        if item.pack_key != self.key:
            raise ValueError("Item of different pack key passed")

        return self.item_sprites[item.id]

    def get_mech_image(self, mech: Mech) -> Image:
        if mech.torso is None:
            raise RuntimeError("Cannot create mech image without torso set")

        torso_sprite = self.get_item_sprite(mech.torso)

        attachments = cast_attachment(torso_sprite.attachment, Type.TORSO)
        renderer = Canvas[str](torso_sprite.image, LAYER_ORDER)

        if mech.legs is not None:
            legs_sprite = self.get_item_sprite(mech.legs)
            leg_attachment = cast_attachment(legs_sprite.attachment, Type.LEGS)
            renderer.add_image(legs_sprite.image, "leg1", leg_attachment, attachments["leg1"])
            renderer.add_image(legs_sprite.image, "leg2", leg_attachment, attachments["leg2"])

        for item, layer in mech.iter_items(weapons=True, slots=True):
            if item is None:
                continue

            item_sprite = self.get_item_sprite(item)
            item_attachment = cast_attachment(item_sprite.attachment, Type.SIDE_WEAPON)
            renderer.add_image(item_sprite.image, layer, item_attachment, attachments[layer])

        if mech.drone is not None:
            drone_sprite = self.get_item_sprite(mech.drone)
            renderer.add_image(
                drone_sprite.image,
                "drone",
                (
                    renderer.offsets.left + drone_sprite.width // 2,
                    renderer.offsets.above + drone_sprite.height + 25,
                ),
            )

        return renderer.merge("torso")


def crop_from_spritesheet(spritesheet: Image, pos: Rectangle) -> Image:
    x, y, w, h = pos["x"], pos["y"], pos["width"], pos["height"]
    return spritesheet.crop((x, y, x + w, y + h))


def resize(image: Image, width: int = 0, height: int = 0) -> Image:
    """Resize image to given width and height.
    Value of 0 preserves original value for the dimension.
    """
    return image.resize((width or image.width, height or image.height))


@define
class RendererStore:
    _renderers: dict[str, PackRenderer] = Factory(dict)
    _asset_cache: dict[str, Image] = Factory(dict)
    """Cache for sprites and alike."""

    def __getitem__(self, key: str) -> PackRenderer:
        return self._renderers[key]

    def __setitem__(self, key: str, value: PackRenderer) -> None:
        self._renderers[key] = value


class ResourceCache:
    def __init__(self) -> None:
        self.cache = dict[t.Any, Image]()

    async def get(self, resource: Resource) -> Image:
        return Image()

    def evict(self) -> None:
        self.cache.clear()
