import io
import logging
from collections import abc
from typing import Final, Protocol

import anyio
import anyio.lowlevel
from PIL import Image

from app.async_utils import amap
from app.models.ids import DEFAULT_PACK_ID, PackId, SpriteId
from app.models.joints import IJoints, Joints
from app.models.sprite_pack import (
    AnySpritePack,
    DynamicSpritePack,
    SpriteKey,
    StaticSpritePack,
    resize,
)
from vec2 import Point2D

import dupermechs.all as sm

_LOG = logging.getLogger("managers")

_sprite_packs: Final[abc.Mapping[PackId, AnySpritePack]] = {}
# pyright does annoying narrowing
_sprite_packs[DEFAULT_PACK_ID] = StaticSpritePack(id=DEFAULT_PACK_ID)
_joints: Final[abc.Mapping[PackId, abc.MutableMapping[SpriteKey, IJoints]]] = {DEFAULT_PACK_ID: {}}


def get_sprite_pack(*, id: PackId = DEFAULT_PACK_ID) -> AnySpritePack:
    return _sprite_packs[id]


async def fetch_image(key: SpriteId, /) -> DynamicSpritePack.FetchResult:
    match get_sprite_pack():
        case DynamicSpritePack() as pack:
            return await pack.fetch_image(key)

        case StaticSpritePack() as pack:
            await anyio.lowlevel.checkpoint_if_cancelled()
            return pack.get_image(key).ok_or(None)


async def fetch_images(*ids: SpriteId) -> list[DynamicSpritePack.FetchResult]:
    match get_sprite_pack():
        case DynamicSpritePack() as pack:
            return await amap(pack.fetch_image, *ids)

        case StaticSpritePack() as pack:
            await anyio.lowlevel.checkpoint_if_cancelled()
            return [pack.get_image(id).ok_or(None) for id in ids]


def get_joints(key: SpriteId, /) -> IJoints | None:
    joints = _joints.get(DEFAULT_PACK_ID)

    if joints is None:
        return None

    return joints.get(key)


def get_image_url(key: SpriteId, /) -> str | None:
    match get_sprite_pack():
        case DynamicSpritePack() as pack:
            resource = pack.image_resources.get(key)

            if resource is None:
                return None

            return resource.uri

        case _:
            return None


def store_sprite_pack(id: PackId, pack: AnySpritePack) -> None:
    match pack:
        case StaticSpritePack():
            image_count = len(pack.images)
            pack_type = "static"

        case DynamicSpritePack():
            image_count = len(pack.image_resources)
            pack_type = "dynamic"

    _LOG.info("Storing sprite pack: %d, type=%s, images=%d", id, pack_type, image_count)
    _sprite_packs[id] = pack


def store_joints(id: PackId, joints: abc.Mapping[SpriteKey, IJoints]) -> None:
    _joints[id] = dict(joints)


class Rectangular(Protocol):
    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...


def create_synthetic_joints(type: sm.Item.Type, rect: Rectangular) -> Joints:
    if type is sm.Item.Type.perk:
        return Joints(torso=Point2D(rect.width // 2, rect.height))

    if type is sm.Item.Type.torso:
        return Joints(
            hat=Point2D(rect.width // 2, rect.height // 10),
            leg_1=Point2D(rect.width * 2 // 5, rect.height * 9 // 10),
            leg_2=Point2D(rect.width * 4 // 5, rect.height * 9 // 10),
            side_weapon_1=Point2D(rect.width // 4, rect.height * 3 // 5),
            side_weapon_2=Point2D(rect.width // 5, rect.height * 3 // 10),
            side_weapon_3=Point2D(rect.width * 3 // 4, rect.height * 3 // 5),
            side_weapon_4=Point2D(rect.width * 4 // 5, rect.height * 3 // 10),
            top_weapon_1=Point2D(rect.width // 4, rect.height // 10),
            top_weapon_2=Point2D(rect.width * 3 // 4, rect.height // 10),
        )

    if type is sm.Item.Type.legs:
        return Joints(
            torso=Point2D(rect.width // 2, rect.height // 10),
            jump_jet=Point2D(rect.width // 2, rect.height),
        )

    if type is sm.Item.Type.side_weapon:
        return Joints(torso=Point2D(rect.width * 3 // 10, rect.height // 2))

    if type is sm.Item.Type.top_weapon:
        return Joints(torso=Point2D(rect.width * 3 // 10, rect.height * 4 // 5))

    return Joints.ZERO


def get_or_create_joints(
    key: SpriteId, image: Rectangular, type: sm.Item.Type, pack_id: PackId = DEFAULT_PACK_ID
) -> IJoints:
    joints = get_joints(key)

    if joints is not None:
        return joints

    _LOG.info("Item %s is missing joints", key)

    _joints[pack_id][key] = joints = create_synthetic_joints(type, image)
    return joints


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
