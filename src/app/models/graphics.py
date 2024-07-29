import logging
import typing

import anyio.lowlevel
import attrs
from PIL import Image

from app.async_utils import async_memoize
from app.core import CONFIG
from resources import HttpResource, Resource

from supermechs.graphics.joints import Joints

__all__ = ("AbstractSprite", "SheetSprite", "SingleSprite")

_LOGGER = logging.getLogger("factories")


@async_memoize
async def load_image(resource: Resource, /) -> "Image.Image":
    from PIL import ImageFile

    _LOGGER.debug("GET %s", resource.uri)

    parser = ImageFile.Parser()

    async for chunk in resource.iter_chunked(CONFIG.chunk_size):
        parser.feed(chunk)
        assert parser.data is not None

        if len(parser.data) > CONFIG.max_image_size:  # pyright: ignore[reportUnknownArgumentType]
            msg = "Image too large"
            raise ValueError(msg)

    return parser.close()


def assure_rgba(image: Image.Image, /) -> Image.Image:
    if image.mode == "RGBA":
        return image

    return image.convert("RGBA")


def resize(image: Image.Image, width: int = 0, height: int = 0) -> Image.Image:
    width = width or image.width
    height = height or image.height

    if image.size == (width, height):
        return image

    return image.resize((width, height))


class AbstractSprite(typing.Protocol):
    @property
    def url(self) -> str | None: ...

    @property
    def joints(self) -> Joints: ...

    async def load(self) -> Image.Image: ...


@attrs.define(kw_only=True)
class ImageLoader:
    resource: Resource
    target_size: tuple[int, int] = (0, 0)
    _image: Image.Image | None = attrs.field(default=None, init=False)

    async def load(self) -> Image.Image:
        if self._image is not None:
            await anyio.lowlevel.checkpoint()
            return self._image

        image = await load_image(self.resource)
        image = assure_rgba(image)
        image = resize(image, *self.target_size)
        self._image = image
        return image


@attrs.define(kw_only=True)
class SingleSprite(ImageLoader):
    joints: Joints

    @property
    def url(self) -> str | None:
        if isinstance(self.resource, HttpResource):
            return self.resource.url

        return None


@attrs.define(kw_only=True)
class SheetSprite:
    sheet: ImageLoader
    boundary: tuple[int, int, int, int]
    joints: Joints
    target_size: tuple[int, int] = (0, 0)
    _image: Image.Image | None = attrs.field(default=None, init=False)

    @property
    def url(self) -> None:
        return None

    async def load(self) -> Image.Image:
        if self._image is not None:
            await anyio.lowlevel.checkpoint()
            return self._image

        sprite_sheet = await self.sheet.load()
        image = sprite_sheet.crop(self.boundary)
        image = assure_rgba(image)
        image = resize(image, *self.target_size)
        self._image = image
        return image
