from collections import abc

import anyio.lowlevel
import attrs
from monads.option import Option
from monads.result import Err, Ok, Result
from monads.tools import from_none
from PIL import Image

from app import aio
from app.async_utils import LockManager
from app.class_utils import limited_repr
from resources import HttpResource

import dupermechs.all as sm

type SpriteKey = tuple[sm.Item.Id, sm.Item.Rarity]
type AnySpritePack = DynamicSpritePack | StaticSpritePack


def resize(image: Image.Image, width: int, height: int) -> Image.Image:
    if width == height == 0:
        return image

    width, height = new_size = (width or image.width, height or image.height)

    # don't resize images that are within 5% margin
    if abs(image.width - width) <= width * 0.05 and abs(image.height - height) <= height * 0.05:
        return image

    return image.resize(new_size)


@attrs.frozen
class StaticSpritePack:
    images: abc.Mapping[SpriteKey, Image.Image] = attrs.field(factory=dict, repr=limited_repr)

    def get_image(self, key: SpriteKey, /) -> Option[Image.Image]:
        return from_none(self.images.get(key))


@attrs.frozen(kw_only=True)
class DynamicSpritePack:
    type FetchResult = Result[Image.Image, aio.UserHttpReadError | None]

    image_resources: abc.Mapping[SpriteKey, HttpResource] = attrs.field(
        factory=dict, repr=limited_repr
    )
    to_resize: abc.MutableMapping[SpriteKey, tuple[int, int]] = attrs.field(
        factory=dict, repr=limited_repr
    )
    images: abc.MutableMapping[SpriteKey, Image.Image] = attrs.field(
        factory=dict, repr=limited_repr
    )
    _request_locks: LockManager[SpriteKey] = attrs.field(factory=LockManager, init=False)

    async def fetch_image(self, key: SpriteKey, /) -> FetchResult:
        """Lookup item's sprite."""
        if (image := self.images.get(key)) is not None:
            await anyio.lowlevel.checkpoint_if_cancelled()
            return Ok(image)

        async with self._request_locks.acquire_for(key):
            if (image := self.images.get(key)) is not None:
                return Ok(image)

            resource = self.image_resources.get(key)

            if resource is None:
                return Err(None)

            match await aio.read_user_resource(resource):
                case Err(err):
                    return Err(err)

                case Ok(bio):
                    image = Image.open(bio).convert(mode="RGBA")

            width, height = self.to_resize.pop(key, (0, 0))
            image = resize(image, width, height)

            self.images[key] = image
            return Ok(image)
