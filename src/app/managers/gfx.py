import io
import logging
from collections import abc

import anyio
import anyio.lowlevel
from PIL import Image

from app.models.sprite_pack import (
    AnySpritePack,
    DynamicSpritePack,
    SpriteKey,
    StaticSpritePack,
    resize,
)
from resources import HttpResource

_LOG = logging.getLogger("managers")
_sprite_pack: AnySpritePack = StaticSpritePack()


def get_sprite_pack() -> AnySpritePack:
    return _sprite_pack


async def fetch_image(key: SpriteKey, /) -> DynamicSpritePack.FetchResult:
    match get_sprite_pack():
        case DynamicSpritePack() as pack:
            return await pack.fetch_image(key)

        case StaticSpritePack() as pack:
            await anyio.lowlevel.checkpoint_if_cancelled()
            return pack.get_image(key).ok_or(None)


def get_image_url(key: SpriteKey, /) -> str | None:
    match get_sprite_pack():
        case DynamicSpritePack() as pack:
            resource = pack.image_resources.get(key)

            if isinstance(resource, HttpResource):
                return resource.uri

            return None

        case _:
            return None


def store_sprite_pack(pack: AnySpritePack, /) -> None:
    global _sprite_pack

    match pack:
        case StaticSpritePack():
            image_count = len(pack.images)
            pack_type = "static"

        case DynamicSpritePack():
            image_count = len(pack.image_resources)
            pack_type = "dynamic"

    _LOG.info("Storing sprite pack: type=%s, images=%d", pack_type, image_count)
    _sprite_pack = pack


def create_sprite_sheet_pack(
    image_bytes: io.BytesIO,
    crop_regions: abc.Mapping[SpriteKey, tuple[int, int, int, int]],
    to_resize: abc.Mapping[SpriteKey, tuple[int, int]] = {},
) -> abc.Mapping[SpriteKey, Image.Image]:
    sheet_image = Image.open(image_bytes).convert(mode="RGBA")
    images: abc.Mapping[SpriteKey, Image.Image] = {}

    for key, rect in crop_regions.items():
        image = sheet_image.crop(rect)

        if new_size := to_resize.get(key):
            width, height = new_size
            image = resize(image, width, height)

        images[key] = image

    return images
