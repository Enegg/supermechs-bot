from collections import abc
from functools import partial
from typing import TypeAlias, assert_never

from attrs import asdict

from smparse.packs.models import (
    AnyItemPack,
    ItemBase,
    ItemPackV1,
    ItemPackV2,
    ItemPackV3,
    ItemV1,
    ItemV3,
    PackBase,
)

import supermechs.all as sm

ItemDict: TypeAlias = dict[sm.abc.ItemID, sm.ItemData]

KNOWN_TAGS = frozenset(map(sm.abc.ItemTag, sm.ItemTagName))


def structure_item(
    data: ItemBase,
    gen_id: abc.Callable[[int], sm.abc.ItemID],
    stages: abc.Sequence[sm.TransformStage],
) -> sm.ItemData:
    return sm.ItemData(
        id=gen_id(data.id),
        name=data.name.unwrap_or("Item"),
        type=sm.abc.ItemType(data.type.unwrap_or(sm.ItemTypeName.PERK)),
        element=sm.abc.ItemElement(data.element.unwrap_or(sm.ItemElementName.PHYSICAL)),
        tags=KNOWN_TAGS.intersection(data.tags),
        stages=stages,
    )


def structure_stages_v1(data: ItemV1) -> abc.Sequence[sm.TransformStage]:
    low, _, hi = data.transform_range.partition("-")

    if not hi:
        hi = low

    if hi:
        hi = hi[0].lower()

        if hi not in "crelmd":
            hi = "c"

    else:
        hi = "c"

    tier_name = next(
        (member for member in sm.StageTierName if member.startswith(hi)), sm.StageTierName.COMMON
    )

    level = sm.StageLevel(power=0, stats=data.stats)
    stage = sm.TransformStage(tier=sm.abc.StageTier(tier_name), levels=(level,))
    return (stage,)


def lerp(value1: float, value2: float, weight: float) -> float:
    return value1 + (value2 - value1) * weight


def interpolate(
    start: sm.ItemStats, end: sm.ItemStats | None, power_levels: abc.Sequence[int]
) -> abc.Sequence[sm.StageLevel]:
    if end is None:
        return (sm.StageLevel(power=power_levels[0], stats=start),)

    levels: list[sm.StageLevel] = []

    start_dict = asdict(start, recurse=False)
    end_dict = asdict(end, recurse=False)

    value1: float
    value2: float

    max_level = len(power_levels) - 1

    for level, power in enumerate(power_levels):
        interpolated: dict[str, float] = {}
        weight = level / max_level
        for key, value1 in start_dict.items():
            value2 = end_dict[key]

            if value2 != 0.0:
                interpolated[key] = lerp(value1, value2, weight)

            else:
                interpolated[key] = value1

        stats = sm.ItemStats(**interpolated)
        levels.append(sm.StageLevel(power=power, stats=stats))

    return tuple(levels)


def make_levels() -> abc.Sequence[sm.StageLevel]: ...


def structure_stages_v3(data: ItemV3) -> abc.Sequence[sm.TransformStage]:
    # TODO: non-base stat objects rely on base stats (see 0 weight on rare+)
    stages: list[sm.TransformStage] = []

    if data.common is not None:
        end = data.max_common or sm.ItemStats.zeros
        levels = interpolate(data.common, end, range(10))
        common = sm.TransformStage(tier=sm.abc.StageTier(sm.StageTierName.COMMON), levels=levels)
        stages.append(common)

    if data.rare is not None:
        levels = interpolate(data.rare, data.max_rare, range(20))
        rare = sm.TransformStage(tier=sm.abc.StageTier(sm.StageTierName.RARE), levels=levels)
        stages.append(rare)

    if data.epic is not None:
        levels = interpolate(data.epic, data.max_epic, range(30))
        epic = sm.TransformStage(tier=sm.abc.StageTier(sm.StageTierName.EPIC), levels=levels)
        stages.append(epic)

    if data.legendary is not None:
        levels = interpolate(data.legendary, data.max_legendary, range(40))
        legendary = sm.TransformStage(
            tier=sm.abc.StageTier(sm.StageTierName.LEGENDARY), levels=levels
        )
        stages.append(legendary)

    if data.mythical is not None:
        levels = interpolate(data.mythical, data.max_mythical, range(50))
        mythical = sm.TransformStage(
            tier=sm.abc.StageTier(sm.StageTierName.MYTHICAL), levels=levels
        )
        stages.append(mythical)

    if data.divine is not None:
        level = sm.StageLevel(power=0, stats=data.divine)
        divine = sm.TransformStage(tier=sm.abc.StageTier(sm.StageTierName.DIVINE), levels=(level,))
        stages.append(divine)

    return tuple(stages)


def gen_id(key: str, id: int) -> sm.abc.ItemID:
    return sm.abc.ItemID(f"{id}{key}")


def restructure(pack: AnyItemPack, /) -> tuple[PackBase, ItemDict]:
    items: dict[sm.abc.ItemID, sm.ItemData] = {}

    match pack:
        case ItemPackV1(config=config, items=raw_items):
            func = partial(gen_id, config.key)

            for raw_item in raw_items:
                item = structure_item(raw_item, func, structure_stages_v1(raw_item))
                items[item.id] = item

            return config, items

        case ItemPackV2(key=key, items=raw_items):
            func = partial(gen_id, key)

            for raw_item in raw_items:
                item = structure_item(raw_item, func, structure_stages_v1(raw_item))
                items[item.id] = item

            return pack, items

        case ItemPackV3(key=key, items=raw_items):
            func = partial(gen_id, key)

            for raw_item in raw_items:
                item = structure_item(raw_item, func, structure_stages_v3(raw_item))
                items[item.id] = item

            return pack, items

    assert_never(pack)
