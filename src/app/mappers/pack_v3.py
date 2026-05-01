import datetime as dt
from collections import abc
from typing import NamedTuple

import app.dto.pack_v3 as dto
from app.models.sprite_pack import SpriteKey

from .common import (
    LITERAL_ELEMENT_TO_ENUM,
    LITERAL_SLOT_TO_ENUM,
    LITERAL_SUBTYPE_TO_ENUM,
    LITERAL_TIER_TO_ENUM,
    ItemMapping,
    convert_stats,
)

import dupermechs.all as sm

type ImageMapping = abc.Mapping[SpriteKey, str]
type SpriteCollection = abc.Sequence[SpriteData]


class SpriteData(NamedTuple):
    item_id: sm.Item.Id
    image: str
    tier: sm.Item.Rarity
    reloaded: bool


def _collect_stages(item: dto.ItemDto, /) -> tuple[abc.Sequence[sm.Item.Stage], SpriteCollection]:
    stages: list[sm.Item.Stage] = []
    images: SpriteCollection = []
    id = sm.Item.Id(item.id)

    for stage_dto in item.stages:
        tier = LITERAL_TIER_TO_ENUM[stage_dto.tier]
        images.append(SpriteData(id, stage_dto.image, tier, item.reloaded))

        levels = [
            sm.Item.Stage.Level(
                level=level_dto.display_level,
                power_required=level_dto.min_power_to_have,
                power_contribution=level_dto.power_contribution,
                stats=convert_stats(level_dto.stats),
            )
            for level_dto in stage_dto.levels
        ]
        if not levels:
            levels.append(sm.Item.Stage.Level(level=1))

        stages.append(sm.Item.Stage(tier=tier, levels=tuple(levels)))

    if not stages:
        stages.append(sm.Item.Stage(tier=sm.Item.Rarity.common, levels=[sm.Item.Stage.Level()]))

    return tuple(stages), images


def _convert_item(item: dto.ItemDto, /) -> tuple[sm.Item, SpriteCollection]:
    stages, images = _collect_stages(item)

    if item.released_at:
        release_date = dt.datetime.fromtimestamp(item.released_at, tz=dt.UTC)
    else:
        release_date = None

    return sm.Item(
        id=sm.Item.Id(item.id),
        name=item.name,
        slot_id=LITERAL_SLOT_TO_ENUM[item.slot_id],
        element=LITERAL_ELEMENT_TO_ENUM[item.element],
        subtype=LITERAL_SUBTYPE_TO_ENUM[item.subtype],
        stages=stages,
        release_date=release_date,
    ), images


class ItemGroups(NamedTuple):
    reloaded: ItemMapping
    legacy: ItemMapping
    hidden: ItemMapping
    images: SpriteCollection


def collect_items(item_dtos: abc.Sequence[dto.ItemDto], /) -> ItemGroups:
    reloaded_items: ItemMapping = {}
    legacy_items: ItemMapping = {}
    hidden_items: ItemMapping = {}
    all_images: SpriteCollection = []

    for item_dto in item_dtos:
        item, images = _convert_item(item_dto)
        all_images += images

        if item_dto.hidden:
            hidden_items[item.id] = item

        elif item_dto.reloaded:
            reloaded_items[item.id] = item

        else:
            legacy_items[item.id] = item

    return ItemGroups(
        reloaded=reloaded_items, legacy=legacy_items, hidden=hidden_items, images=all_images
    )
