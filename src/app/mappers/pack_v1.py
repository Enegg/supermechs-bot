from collections import abc
from typing import NamedTuple

import msgspec

import app.dto.pack_v1 as dto
from app.mappers.common import LITERAL_ELEMENT_TO_ENUM, LITERAL_TYPE_TO_ENUM, ItemMapping
from app.mappers.common_v1_v2 import stats_to_stages
from app.models.sprite_pack import SpriteKey
from resources import HttpResource

import dupermechs.all as sm


def convert_item(item: dto.ItemDto, /) -> sm.Item:
    return sm.Item(
        id=sm.Item.Id(item.id),
        name=item.name,
        type=LITERAL_TYPE_TO_ENUM[item.type],
        element=LITERAL_ELEMENT_TO_ENUM[item.element],
        stages=stats_to_stages(item.stats, item.transform_range),
    )


def _get_base_url(pack_dto: dto.ItemPackDto, /) -> str:
    if pack_dto.base_url is not msgspec.UNSET:
        return pack_dto.base_url

    if pack_dto.config is msgspec.UNSET:
        return ""

    if pack_dto.config.base_url is not msgspec.UNSET:
        return pack_dto.config.base_url

    return ""


class ConversionResult(NamedTuple):
    items: ItemMapping
    images: abc.Mapping[SpriteKey, HttpResource]


def convert_pack_v1(pack_dto: dto.ItemPackDto, /) -> ConversionResult:
    items: ItemMapping = {}
    images: abc.Mapping[SpriteKey, HttpResource] = {}
    base_url = _get_base_url(pack_dto)

    for item_dto in pack_dto.items:
        item = convert_item(item_dto)
        items[item.id] = item
        sprite_key = (item.id, item.stages[-1].tier)

        if item_dto.image is not msgspec.UNSET:
            images[sprite_key] = HttpResource.from_uri(item_dto.image.replace("%url%", base_url))

    return ConversionResult(items, images)
