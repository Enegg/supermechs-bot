import logging
from collections import abc

import msgspec
from monads.result import Err, Ok

from app import aio, init
from app.dto.gfx_v3 import GfxPackDto
from app.dto.pack_v3 import ItemPackDto as ItemPackDtoV3
from app.mappers.pack_v3 import SpriteCollection, collect_items
from app.models.item_pack import ItemPack
from app.models.sprite_pack import SpritePack
from resources import AnyResource, HttpResource

_LOG = logging.getLogger("init")


class VersionDto(msgspec.Struct):
    version: str = "1"


def safe_decode[T](data: abc.Buffer | str, /, *, type: type[T]) -> T | None:
    try:
        return msgspec.json.decode(data, type=type)

    except msgspec.DecodeError as exc:
        _LOG.error("Could not decode %s:", type.__name__, exc_info=exc)
        return None


async def load_datapack(
    item_pack_uri: AnyResource, gfx_pack_uri: AnyResource | None, /, session: aio.HTTPSession
) -> None:
    match await aio.read_resource(item_pack_uri, session):
        case Err(exc):
            _LOG.error("Could not read %s:", item_pack_uri.uri, exc_info=exc)
            return

        case Ok(data):
            version_dto = safe_decode(data, type=VersionDto)

    if version_dto is None:
        return

    if version_dto.version != "3":
        _LOG.error("Unknown data pack version: %s", version_dto.version)
        return

    _LOG.info("Datapack version: %s", version_dto.version)

    dto = safe_decode(data, type=ItemPackDtoV3)

    if dto is None:
        return

    item_groups = collect_items(dto.items)
    item_pack = ItemPack(
        reloaded_items=item_groups.reloaded,
        legacy_items=item_groups.legacy,
        hidden_items=item_groups.hidden,
    )
    init.set_item_pack(item_pack)

    if gfx_pack_uri is None:
        _LOG.warning(f"{gfx_pack_uri=}, graphics pack not configured")

    else:
        await load_gfx_v3(gfx_pack_uri, item_groups.images, session)


async def load_gfx_v3(
    gfx_pack_uri: AnyResource, images: SpriteCollection, session: aio.HTTPSession
) -> None:
    match await aio.read_resource(gfx_pack_uri, session):
        case Err(exc):
            _LOG.error("Could not read %s:", gfx_pack_uri.uri, exc_info=exc)
            return

        case Ok(gfx_data):
            gfx_dto = safe_decode(gfx_data, type=GfxPackDto)

    if gfx_dto is None:
        return

    image_resources: SpritePack = {}
    sprite_table = {(sprite.gfx, sprite.reloaded): sprite for sprite in gfx_dto.sprites}

    for image_data in images:
        sprite_dto = sprite_table.get((image_data.image, image_data.reloaded))

        if sprite_dto is None:
            continue

        image_resources[image_data.item_id, image_data.tier] = HttpResource.from_uri(
            sprite_dto.image.replace("%url%", gfx_dto.base_url)
        )

    init.set_sprite_pack(image_resources)
