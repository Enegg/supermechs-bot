import logging

import msgspec
from monads.result import Err, Ok

from app import aio
from app.core import CONFIG
from app.dto.gfx_v3 import GfxPackDto
from app.dto.pack_v1 import ItemPackDto as ItemPackDtoV1
from app.dto.pack_v2 import ItemPackDto as ItemPackDtoV2
from app.dto.pack_v3 import ItemPackDto as ItemPackDtoV3
from app.mappers.common_gfx import JointsMapping
from app.mappers.pack_v1 import convert_pack_v1
from app.mappers.pack_v3 import collect_items, convert_joints
from app.models.ids import DEFAULT_PACK_ID
from app.models.item_pack import ItemPack
from app.models.sprite_pack import DynamicSpritePack, SpriteKey
from resources import HttpResource

from . import gfx, packs

_LOG = logging.getLogger("managers")


class VersionDto(msgspec.Struct):
    version: str = "1"


async def load_datapack() -> None:
    if CONFIG.item_pack_uri is None:
        _LOG.warning(f"{CONFIG.item_pack_uri=}, item pack not configured")
        return

    match await aio.read_resource(CONFIG.item_pack_uri):
        case Err(exc):
            _LOG.error(f"Could not read {CONFIG.item_pack_uri.uri}:", exc_info=exc)
            return

        case Ok(data):
            version_dto = msgspec.json.decode(data, type=VersionDto)

    match version_dto.version:
        case "1":
            dto = msgspec.json.decode(data, type=ItemPackDtoV1)
            pack_v1 = convert_pack_v1(dto)

            if dto.legacy:
                item_pack = ItemPack(id=DEFAULT_PACK_ID, legacy_items=pack_v1.items)

            else:
                item_pack = ItemPack(id=DEFAULT_PACK_ID, reloaded_items=pack_v1.items)

            packs.store_item_pack(item_pack)
            sprite_pack = DynamicSpritePack(id=DEFAULT_PACK_ID, image_resources=pack_v1.images)
            gfx.store_sprite_pack(DEFAULT_PACK_ID, sprite_pack)
            gfx.store_joints(DEFAULT_PACK_ID, pack_v1.joints)
            return

        case "2":
            dto = msgspec.json.decode(data, type=ItemPackDtoV2)
            _LOG.error("TODO: V2")
            return

        case "3":
            dto = msgspec.json.decode(data, type=ItemPackDtoV3)
            item_groups = collect_items(dto.items)
            item_pack = ItemPack(
                id=DEFAULT_PACK_ID,
                reloaded_items=item_groups.reloaded,
                legacy_items=item_groups.legacy,
                hidden_items=item_groups.hidden,
            )
            packs.store_item_pack(item_pack)

            if CONFIG.gfx_pack_uri is None:
                _LOG.warning(f"{CONFIG.gfx_pack_uri=}, graphics pack not configured")
                return

            match await aio.read_resource(CONFIG.gfx_pack_uri):
                case Err(exc):
                    _LOG.error(f"Could not read {CONFIG.gfx_pack_uri.uri}:", exc_info=exc)
                    return

                case Ok(gfx_data):
                    gfx_dto = msgspec.json.decode(gfx_data, type=GfxPackDto)

            joints: JointsMapping = {}
            image_resources: dict[SpriteKey, HttpResource] = {}

            sprite_table = {(sprite.gfx, sprite.reloaded): sprite for sprite in gfx_dto.sprites}

            for image_data in item_groups.images:
                sprite_dto = sprite_table.get((image_data.image, image_data.reloaded))

                if sprite_dto is None:
                    continue

                sprite_key = image_data.item_id, image_data.tier

                image_resources[sprite_key] = HttpResource.from_uri(
                    sprite_dto.image.replace("%url%", gfx_dto.base_url)
                )

                if sprite_dto.joint is not msgspec.UNSET:
                    joints[sprite_key] = convert_joints(sprite_dto.joint)

            sprite_pack = DynamicSpritePack(id=DEFAULT_PACK_ID, image_resources=image_resources)
            gfx.store_sprite_pack(DEFAULT_PACK_ID, sprite_pack)
            gfx.store_joints(DEFAULT_PACK_ID, joints)

        case unknown:
            _LOG.error(f"Unknown data pack version: {unknown}")
            return
