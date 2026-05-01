from collections import abc
from typing import NamedTuple

import msgspec

import app.dto.pack_v1 as dto
from app.mappers.common import (
    LITERAL_ELEMENT_TO_ENUM,
    LITERAL_SLOT_TO_ENUM,
    ItemMapping,
    stats_to_stages,
)
from app.models.sprite_pack import SpriteKey
from resources import HttpResource

import dupermechs.all as sm


class ConversionResultV1(NamedTuple):
    items: ItemMapping
    images: abc.Mapping[SpriteKey, HttpResource]


def convert_pack_v1(pack_dto: dto.ItemPackDto, /) -> ConversionResultV1:
    items: ItemMapping = {}
    images: abc.Mapping[SpriteKey, HttpResource] = {}

    if pack_dto.base_url is not msgspec.UNSET:
        base_url = pack_dto.base_url

    elif pack_dto.config is not msgspec.UNSET and pack_dto.config.base_url is not msgspec.UNSET:
        base_url = pack_dto.config.base_url

    else:
        base_url = ""

    for item_dto in pack_dto.items:
        item = sm.Item(
            id=sm.Item.Id(item_dto.id),
            name=item_dto.name,
            slot_id=LITERAL_SLOT_TO_ENUM[item_dto.slot_id],
            element=LITERAL_ELEMENT_TO_ENUM[item_dto.element],
            stages=stats_to_stages(item_dto.stats, item_dto.transform_range),
        )
        items[item.id] = item
        sprite_key = (item.id, item.stages[-1].tier)

        if item_dto.image is not msgspec.UNSET:
            images[sprite_key] = HttpResource.from_uri(item_dto.image.replace("%url%", base_url))

    return ConversionResultV1(items, images)
