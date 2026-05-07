
import app.dto.pack_v2 as dto
from app.mappers.common import (
    LITERAL_ELEMENT_TO_ENUM,
    LITERAL_SLOT_TO_ENUM,
    ItemMapping,
    stats_to_stages,
)

import dupermechs.all as sm


def convert_pack_v2(pack_dto: dto.ItemPackDto, /) -> ItemMapping:
    items: ItemMapping = {}

    for item_dto in pack_dto.items:
        item = sm.Item(
            id=sm.Item.Id(item_dto.id),
            name=item_dto.name,
            slot_id=LITERAL_SLOT_TO_ENUM[item_dto.slot_id],
            element=LITERAL_ELEMENT_TO_ENUM[item_dto.element],
            stages=stats_to_stages(item_dto.stats, item_dto.transform_range),
        )
        items[item.id] = item

    return items
