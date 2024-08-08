import logging
from collections import abc

import attrs

from app.models import ItemPack
from app.models.graphics import AbstractSprite, ImageLoader, SheetSprite, SingleSprite
from app.models.item_pack import SpriteKey
from resources import resource
from sm.parse import ItemWithStats, ItemWithTiers, PackData, Rectangle, parse_item_pack
from sm.parse.items import Point2D, TorsoAttachment

from supermechs.abc.item import ItemID
from supermechs.abc.item_pack import PackKey
from supermechs.api import ItemData, Tier, TransformStage, Type
from supermechs.ext.deserializers import to_joints, to_stats_mapping, to_tags
from supermechs.ext.deserializers.stat_providers import StaticStats
from supermechs.ext.deserializers.typedefs import AnyItemPack
from supermechs.graphics.api import Joints

_LOGGER = logging.getLogger("sm.converter")


def levels_for_tier(rarity: Tier, tier: Tier) -> abc.Sequence[int]:
    return [0]


def stages_from_stats(item: ItemWithStats, /) -> TransformStage:
    lower = item.transform_range.lower
    upper = item.transform_range.upper

    stage = TransformStage(
        tier=upper,
        stats=StaticStats(to_stats_mapping(item.stats)),
        level_progression=levels_for_tier(lower, upper),
    )

    for i in reversed(range(lower, upper)):
        tier = Tier.of_value(i)
        stage = TransformStage(
            tier=tier,
            stats=StaticStats({}),
            level_progression=levels_for_tier(lower, tier),
            next=stage,
        )

    return stage


def stages_from_tiers(item: ItemWithTiers, /) -> TransformStage:
    lower = item.transform_range.lower
    upper = item.transform_range.upper
    # TODO
    raise NotImplementedError


def to_item_data(data_item: ItemWithStats | ItemWithTiers, pack_key: PackKey) -> ItemData:
    if isinstance(data_item, ItemWithStats):
        stage = stages_from_stats(data_item)

    else:
        stage = stages_from_tiers(data_item)

    return ItemData(
        id=data_item.id,
        pack_key=pack_key,
        name=data_item.name,
        type=data_item.type if isinstance(data_item.type, Type) else Type.TORSO,
        element=data_item.element,
        tags=to_tags(data_item.tags, stage),
        start_stage=stage,
    )


def rect_to_boundary(rect: Rectangle, /) -> tuple[int, int, int, int]:
    return (rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)


def _convert_joints(joints: Point2D | TorsoAttachment | None, /) -> Joints:
    if joints is None:
        return {}

    data = attrs.asdict(joints)
    return to_joints(data)


def sprites_from_sheet(pack_data: PackData, /) -> dict[SpriteKey, AbstractSprite]:
    if not pack_data.sprites_sheet:
        return {}

    image_loader = ImageLoader(resource=resource(pack_data.sprites_sheet))
    sprites: dict[SpriteKey, AbstractSprite] = {}

    for item in pack_data.items:
        key = item.name.replace(" ", "")

        rect = pack_data.sprites_map.get(key) or pack_data.sprites_map.get(item.name)

        if rect is None:
            _LOGGER.info("Item %s missing rectangle", item.name)
            continue

        boundary = rect_to_boundary(rect)
        sprite = SheetSprite(
            sheet=image_loader,
            boundary=boundary,
            joints=_convert_joints(item.joints),
            target_size=(item.width, item.height),
        )
        sprites[item.id, item.transform_range.upper] = sprite

    return sprites


def sprites_from_items(pack_data: PackData, /) -> dict[SpriteKey, AbstractSprite]:
    sprites: dict[SpriteKey, AbstractSprite] = {}

    for item in pack_data.items:
        if item.image is None:
            continue

        sprite = SingleSprite(
            resource=resource(item.image.replace("%url%", pack_data.base_url)),
            joints=_convert_joints(item.joints),
            target_size=(item.width, item.height),
        )
        sprites[item.id, item.transform_range.upper] = sprite

    return sprites


def to_item_pack(data: AnyItemPack, /) -> ItemPack:
    pack_data = parse_item_pack(data)

    sprites = sprites_from_sheet(pack_data)
    sprites |= sprites_from_items(pack_data)

    items = dict[ItemID, ItemData]()

    for item_data in pack_data.items:
        item = to_item_data(item_data, pack_data.key)
        items[item.id] = item

    return ItemPack(
        key=pack_data.key,
        name=pack_data.name,
        description=pack_data.description,
        items=items,
        sprites=sprites,
    )
