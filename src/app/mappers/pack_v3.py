from collections import abc
from typing import NamedTuple

from app.dto.gfx_v3 import JointDto
from app.dto.pack_v3 import ItemDto
from app.models.joints import Joints
from app.models.sprite_pack import SpriteKey

from .common import (
    LITERAL_ELEMENT_TO_ENUM,
    LITERAL_TIER_TO_ENUM,
    LITERAL_TYPE_TO_ENUM,
    ItemMapping,
    convert_stats,
)
from .common_gfx import convert_point_2d

import dupermechs.all as sm

type ImageMapping = abc.Mapping[SpriteKey, str]
type SpriteCollection = abc.Sequence[SpriteData]


class SpriteData(NamedTuple):
    item_id: sm.Item.Id
    image: str
    tier: sm.Item.Rarity
    reloaded: bool


def _determine_element(item: ItemDto, /) -> sm.Item.Element:
    if item.element != "OTHER":
        return LITERAL_ELEMENT_TO_ENUM[item.element]

    if item.subtype == "energyHeat":
        return sm.Item.Element.combined

    return sm.Item.Element.other


def _collect_stages(item: ItemDto, /) -> tuple[abc.Sequence[sm.Item.Stage], SpriteCollection]:
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
        assert levels
        stages.append(sm.Item.Stage(tier=tier, levels=tuple(levels)))

    assert stages
    return tuple(stages), images


def _convert_item(item: ItemDto, /) -> tuple[sm.Item, SpriteCollection]:
    stages, images = _collect_stages(item)
    return sm.Item(
        id=sm.Item.Id(item.id),
        name=item.name,
        type=LITERAL_TYPE_TO_ENUM[item.type],
        element=_determine_element(item),
        stages=stages,
    ), images


class ItemGroups(NamedTuple):
    reloaded: ItemMapping
    legacy: ItemMapping
    hidden: ItemMapping
    images: SpriteCollection


def collect_items(item_dtos: abc.Sequence[ItemDto], /) -> ItemGroups:
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


def convert_joints(joint_dto: JointDto, /) -> Joints:
    return Joints(
        torso=convert_point_2d(joint_dto.torso),
        leg_1=convert_point_2d(joint_dto.leg1),
        leg_2=convert_point_2d(joint_dto.leg2),
        side_weapon_1=convert_point_2d(joint_dto.side1),
        side_weapon_2=convert_point_2d(joint_dto.side2),
        side_weapon_3=convert_point_2d(joint_dto.side3),
        side_weapon_4=convert_point_2d(joint_dto.side4),
        top_weapon_1=convert_point_2d(joint_dto.top1),
        top_weapon_2=convert_point_2d(joint_dto.top2),
    )
