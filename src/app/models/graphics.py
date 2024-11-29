import io
import logging
from collections import abc
from typing import ClassVar, Protocol, Self, TypeAlias

import anyio.lowlevel
import attrs
from aiohttp import ClientSession
from PIL import Image

from app.async_utils import read_content
from app.typeshed import AsyncFunc, Pathish
from vec2 import Point2D

from supermechs.all import ItemTypeName, abc as smabc

_LOG = logging.getLogger(__name__)

SpriteKey: TypeAlias = tuple[smabc.ItemID, smabc.StageTier]
ImageLoader: TypeAlias = AsyncFunc[[str], Image.Image]
Processor: TypeAlias = abc.Callable[[Image.Image], Image.Image]


@attrs.frozen(kw_only=True)
class Joints:
    ZERO: ClassVar[Self]

    hat: Point2D = Point2D.ZERO
    torso: Point2D = Point2D.ZERO
    leg_1: Point2D = Point2D.ZERO
    leg_2: Point2D = Point2D.ZERO
    side_weapon_1: Point2D = Point2D.ZERO
    side_weapon_2: Point2D = Point2D.ZERO
    side_weapon_3: Point2D = Point2D.ZERO
    side_weapon_4: Point2D = Point2D.ZERO
    top_weapon_1: Point2D = Point2D.ZERO
    top_weapon_2: Point2D = Point2D.ZERO


Joints.ZERO = Joints()


class Rectangular(Protocol):
    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...


def create_synthetic_joints(type: smabc.ItemType, rect: Rectangular) -> Joints:  # noqa: A002
    if type == ItemTypeName.PERK:
        return Joints(torso=Point2D(0.5 * rect.width))

    if type == ItemTypeName.TORSO:
        return Joints(
            hat=Point2D(0.5 * rect.width, 0.1 * rect.height),
            leg_1=Point2D(0.4 * rect.width, 0.9 * rect.height),
            leg_2=Point2D(0.8 * rect.width, 0.9 * rect.height),
            side_weapon_1=Point2D(0.25 * rect.width, 0.6 * rect.height),
            side_weapon_2=Point2D(0.20 * rect.width, 0.3 * rect.height),
            side_weapon_3=Point2D(0.75 * rect.width, 0.6 * rect.height),
            side_weapon_4=Point2D(0.80 * rect.width, 0.3 * rect.height),
            top_weapon_1=Point2D(0.25 * rect.width, 0.1 * rect.height),
            top_weapon_2=Point2D(0.75 * rect.width, 0.1 * rect.height),
        )

    if type == ItemTypeName.LEGS:
        return Joints(torso=Point2D(0.5 * rect.width, 0.1 * rect.height))

    if type == ItemTypeName.SIDE_WEAPON:
        return Joints(torso=Point2D(0.3 * rect.width, 0.5 * rect.height))

    if type == ItemTypeName.TOP_WEAPON:
        return Joints(torso=Point2D(0.3 * rect.width, 0.8 * rect.height))

    return Joints.ZERO


# ----------------------------------------- image loaders ------------------------------------------
async def read_image(uri: Pathish, /) -> Image.Image:
    path = anyio.Path(uri)
    data = await path.read_bytes()
    _LOG.info("OPEN %s, size %d", uri, len(data))
    bio = io.BytesIO(data)
    return Image.open(bio).convert(mode="RGBA")


@attrs.define
class FetchImage:
    session: ClassVar[ClientSession]
    max_size: int | None = None
    chunk_size: int = -1

    async def __call__(self, uri: str, /) -> Image.Image:
        async with self.session.get(uri) as response:
            response.raise_for_status()

            bio = await read_content(response, self.max_size, self.chunk_size)
        return Image.open(bio).convert(mode="RGBA")


@attrs.define
class CacheImage:
    loader: ImageLoader
    image: Image.Image | None = None

    async def __call__(self, uri: str, /) -> Image.Image:
        if self.image is not None:
            await anyio.lowlevel.checkpoint()
            return self.image

        self.image = await self.loader(uri)
        return self.image


# ------------------------------------------- processors -------------------------------------------
def resize(width: int = 0, height: int = 0) -> Processor:
    def process(image: Image.Image, /) -> Image.Image:
        new_size = (width or image.width, height or image.height)

        if image.size == new_size:
            return image

        return image.resize(new_size)

    return process


def crop(boundary: tuple[int, int, int, int]) -> Processor:
    def process(sprite_sheet: Image.Image, /) -> Image.Image:
        return sprite_sheet.crop(boundary)

    return process


# ------------------------------------------ dataclasses -------------------------------------------
class Sprite(Protocol):
    @property
    def url(self) -> str | None: ...
    @property
    def joints(self) -> Joints: ...
    def load(self) -> abc.Awaitable[Image.Image]: ...


@attrs.define
class LoadedSprite:
    url: str | None
    image: Image.Image
    joints: Joints

    async def load(self) -> Image.Image:
        await anyio.lowlevel.checkpoint()
        return self.image


@attrs.define
class ImageRequest:
    uri: str
    loader: ImageLoader
    url: str | None = None
    processors: abc.Sequence[Processor] = ()

    async def load(self) -> Image.Image:
        image = await self.loader(self.uri)

        for processor in self.processors:
            image = processor(image)

        return image


@attrs.define
class PendingSprite:
    request: ImageRequest
    key: SpriteKey
    on_load: abc.Callable[[SpriteKey, LoadedSprite], None]
    joints: Joints = Joints.ZERO

    @property
    def url(self) -> str | None:
        return self.request.url

    async def load(self) -> Image.Image:
        image = await self.request.load()
        joints = self.joints

        if joints == Joints.ZERO:
            _LOG.info("Joints for %s are all zero", self.key)

        loaded_sprite = LoadedSprite(self.request.url, image, self.joints)
        self.on_load(self.key, loaded_sprite)

        return image
