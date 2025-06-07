from typing import NamedTuple

import app.dto.pack_v2 as dto
from app.mappers.common import LITERAL_ELEMENT_TO_ENUM, LITERAL_TYPE_TO_ENUM, ItemMapping
from app.mappers.common_v1_v2 import stats_to_stages

import dupermechs.all as sm


def convert_item(item: dto.ItemDto, /) -> sm.Item:
    return sm.Item(
        id=sm.Item.Id(item.id),
        name=item.name,
        type=LITERAL_TYPE_TO_ENUM[item.type],
        element=LITERAL_ELEMENT_TO_ENUM[item.element],
        stages=stats_to_stages(item.stats, item.transform_range),
    )


class ConversionResult(NamedTuple):
    items: ItemMapping


def convert_pack_v2(pack_dto: dto.ItemPackDto, /) -> ConversionResult:
    items: ItemMapping = {}

    for item_dto in pack_dto.items:
        item = convert_item(item_dto)
        items[item.id] = item

    return ConversionResult(items=items)
