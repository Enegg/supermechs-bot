import logging

import msgspec
from monads.result import Err, Ok

from app import aio
from app.dto.gfx_v3 import GfxPackDto
from app.dto.pack_v1 import ItemPackDto as ItemPackDtoV1
from app.dto.pack_v2 import ItemPackDto as ItemPackDtoV2
from app.dto.pack_v3 import ItemPackDto as ItemPackDtoV3
from app.mappers.pack_v1 import convert_pack_v1
from app.mappers.pack_v2 import convert_pack_v2
from app.mappers.pack_v3 import SpriteCollection, collect_items
from app.models.item_pack import ItemPack
from app.models.sprite_pack import DynamicSpritePack, SpriteKey
from resources import AnyResource, HttpResource

from . import gfx, packs

_LOG = logging.getLogger("managers")


class VersionDto(msgspec.Struct):
    version: str = "1"


async def load_datapack(item_pack_uri: AnyResource, gfx_pack_uri: AnyResource | None, /) -> None:
    match await aio.read_resource(item_pack_uri):
        case Err(exc):
            _LOG.error(f"Could not read {item_pack_uri.uri}:", exc_info=exc)
            return

        case Ok(data):
            version_dto = msgspec.json.decode(data, type=VersionDto)

    match version_dto.version:
        case "1":
            dto = msgspec.json.decode(data, type=ItemPackDtoV1)
            pack_v1 = convert_pack_v1(dto)

            if dto.legacy:
                item_pack = ItemPack(legacy_items=pack_v1.items)

            else:
                item_pack = ItemPack(reloaded_items=pack_v1.items)

            packs.store_item_pack(item_pack)
            sprite_pack = DynamicSpritePack(image_resources=pack_v1.images)
            gfx.store_sprite_pack(sprite_pack)

        case "2":
            dto = msgspec.json.decode(data, type=ItemPackDtoV2)
            pack_v2 = convert_pack_v2(dto)
            item_pack = ItemPack(reloaded_items=pack_v2)
            packs.store_item_pack(item_pack)

        case "3":
            dto = msgspec.json.decode(data, type=ItemPackDtoV3)
            item_groups = collect_items(dto.items)
            item_pack = ItemPack(
                reloaded_items=item_groups.reloaded,
                legacy_items=item_groups.legacy,
                hidden_items=item_groups.hidden,
            )
            packs.store_item_pack(item_pack)

            if gfx_pack_uri is None:
                _LOG.warning(f"{gfx_pack_uri=}, graphics pack not configured")

            else:
                await load_gfx_v3(gfx_pack_uri, item_groups.images)

        case unknown:
            _LOG.error(f"Unknown data pack version: {unknown}")


async def load_gfx_v3(gfx_pack_uri: AnyResource, images: SpriteCollection) -> None:
    match await aio.read_resource(gfx_pack_uri):
        case Err(exc):
            _LOG.error(f"Could not read {gfx_pack_uri.uri}:", exc_info=exc)
            return

        case Ok(gfx_data):
            gfx_dto = msgspec.json.decode(gfx_data, type=GfxPackDto)

    image_resources: dict[SpriteKey, HttpResource] = {}

    sprite_table = {(sprite.gfx, sprite.reloaded): sprite for sprite in gfx_dto.sprites}

    for image_data in images:
        sprite_dto = sprite_table.get((image_data.image, image_data.reloaded))

        if sprite_dto is None:
            continue

        image_resources[image_data.item_id, image_data.tier] = HttpResource.from_uri(
            sprite_dto.image.replace("%url%", gfx_dto.base_url)
        )

    sprite_pack = DynamicSpritePack(image_resources=image_resources)
    gfx.store_sprite_pack(sprite_pack)
