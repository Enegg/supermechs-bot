import math
from collections import abc

from app import i18n
from app.assets import EMOJIS

import dupermechs.all as sm
from dupermechs.enums import ItemStat

MAX_EMOJIS = 4
"""Threshold for multiple emojis shown inline in the stats field."""


def format_float(num: float, decimals: int) -> str:
    num = round(float(num), decimals)

    if num.is_integer():
        return f"{num:.0f}"

    return f"{num:.{decimals}f}"


def format_damage_default(lo: int, hi: int, /) -> str:
    if hi and lo != hi:
        return f"{lo}-{hi}"

    return str(lo)


def format_damage_average(lo: int | float, hi: int | float, /, *, decimals: int = 1) -> str:
    mean = (lo + hi) / 2
    dev = math.sqrt(((lo - mean) ** 2 + (hi - mean) ** 2) / 2) / mean * 100.0
    str_mean = format_float(mean, 1)
    str_dev = format_float(dev, decimals)
    return f"{str_mean} ±{str_dev}%"


def format_range(lo: int, hi: int, /) -> str:
    if hi <= 0:
        return f"{lo}+"

    if lo == hi:
        return str(lo)

    return f"{lo}-{hi}"


def item_transform_range(item: sm.IItem, /, stage_index: int = -1) -> str:
    str_range: list[str] = [EMOJIS.tiers.get_hollow(stage.tier) for stage in item.stages]
    str_range[stage_index] = EMOJIS.tiers[item.stages[stage_index].tier]
    return "".join(str_range)


def has_damage_spread(stats: sm.IItemStats, /) -> bool:
    return (
        stats.physical_damage != stats.physical_damage_addon
        or stats.explosive_damage != stats.explosive_damage_addon
        or stats.electric_damage != stats.electric_damage_addon
    )


def has_damage(stats: sm.IItemStats, /) -> bool:
    return stats.physical_damage != 0 or stats.explosive_damage != 0 or stats.electric_damage != 0


def has_buff_affected_stats(stats: sm.IItemStats, /) -> bool:
    return (
        stats.energy_capacity != 0
        or stats.energy_regeneration != 0
        or stats.energy_damage != 0
        or stats.heat_capacity != 0
        or stats.heat_cooling != 0
        or stats.heat_damage != 0
        or stats.physical_damage != 0
        or stats.explosive_damage != 0
        or stats.electric_damage != 0
        or stats.physical_resistance != 0
        or stats.explosive_resistance != 0
        or stats.electric_resistance != 0
        or stats.backfire != 0
    )


def format_stats(
    item_stats: sm.IItemStats, gettext: i18n.GetText, *, avg: bool
) -> tuple[list[str], list[str]]:
    def fmt(emoji: str, value: int | str, stat_key: ItemStat, /) -> str:
        return f"{emoji} **{value}** {gettext.get_stat_name(stat_key)}"

    format_damage: abc.Callable[[int, int], str] = (
        format_damage_average if avg else format_damage_default
    )

    stats_lines: list[str] = []
    costs_lines: list[str] = []
    emojis = EMOJIS.stats

    if item_stats.weight:
        stats_lines.append(fmt(emojis.weight, item_stats.weight, ItemStat.weight))
    if item_stats.hit_points:
        stats_lines.append(fmt(emojis.hit_points, item_stats.hit_points, ItemStat.hit_points))
    if item_stats.energy_capacity:
        stats_lines.append(
            fmt(emojis.energy_capacity, item_stats.energy_capacity, ItemStat.energy_capacity)
        )
    if item_stats.energy_regeneration:
        stats_lines.append(
            fmt(
                emojis.energy_regeneration,
                item_stats.energy_regeneration,
                ItemStat.energy_regeneration,
            )
        )
    if item_stats.heat_capacity:
        stats_lines.append(
            fmt(emojis.heat_capacity, item_stats.heat_capacity, ItemStat.heat_capacity)
        )
    if item_stats.heat_cooling:
        stats_lines.append(fmt(emojis.heat_cooling, item_stats.heat_cooling, ItemStat.heat_cooling))
    if item_stats.physical_resistance:
        stats_lines.append(
            fmt(
                emojis.physical_resistance,
                item_stats.physical_resistance,
                ItemStat.physical_resistance,
            )
        )
    if item_stats.explosive_resistance:
        stats_lines.append(
            fmt(
                emojis.explosive_resistance,
                item_stats.explosive_resistance,
                ItemStat.explosive_resistance,
            )
        )
    if item_stats.electric_resistance:
        stats_lines.append(
            fmt(
                emojis.electric_resistance,
                item_stats.electric_resistance,
                ItemStat.electric_resistance,
            )
        )
    if item_stats.bullets_capacity:
        stats_lines.append(
            fmt(
                emojis.bullets_capacity,
                item_stats.bullets_capacity,
                ItemStat.bullets_capacity,
            )
        )
    if item_stats.rockets_capacity:
        stats_lines.append(
            fmt(
                emojis.rockets_capacity,
                item_stats.rockets_capacity,
                ItemStat.rockets_capacity,
            )
        )
    if item_stats.physical_damage:
        stats_lines.append(
            fmt(
                emojis.physical_damage,
                format_damage(item_stats.physical_damage, item_stats.physical_damage_addon),
                ItemStat.physical_damage,
            )
        )
    if item_stats.physical_resistance_damage:
        stats_lines.append(
            fmt(
                emojis.physical_resistance_damage,
                item_stats.physical_resistance_damage,
                ItemStat.physical_resistance_damage,
            )
        )
    if item_stats.electric_damage:
        stats_lines.append(
            fmt(
                emojis.electric_damage,
                format_damage(item_stats.electric_damage, item_stats.electric_damage_addon),
                ItemStat.electric_damage,
            )
        )
    if item_stats.energy_damage:
        stats_lines.append(
            fmt(emojis.energy_damage, item_stats.energy_damage, ItemStat.energy_damage)
        )
    if item_stats.energy_capacity_damage:
        stats_lines.append(
            fmt(
                emojis.energy_capacity_damage,
                item_stats.energy_capacity_damage,
                ItemStat.energy_capacity_damage,
            )
        )
    if item_stats.regeneration_damage:
        stats_lines.append(
            fmt(
                emojis.regeneration_damage,
                item_stats.regeneration_damage,
                ItemStat.regeneration_damage,
            )
        )
    if item_stats.electric_resistance_damage:
        stats_lines.append(
            fmt(
                emojis.electric_resistance_damage,
                item_stats.electric_resistance_damage,
                ItemStat.electric_resistance_damage,
            )
        )
    if item_stats.explosive_damage:
        stats_lines.append(
            fmt(
                emojis.explosive_damage,
                format_damage(item_stats.explosive_damage, item_stats.explosive_damage_addon),
                ItemStat.explosive_damage,
            )
        )
    if item_stats.heat_damage:
        stats_lines.append(fmt(emojis.heat_damage, item_stats.heat_damage, ItemStat.heat_damage))
    if item_stats.heat_capacity_damage:
        stats_lines.append(
            fmt(
                emojis.heat_capacity_damage,
                item_stats.heat_capacity_damage,
                ItemStat.heat_capacity_damage,
            )
        )
    if item_stats.cooling_damage:
        stats_lines.append(
            fmt(emojis.cooling_damage, item_stats.cooling_damage, ItemStat.cooling_damage)
        )
    if item_stats.explosive_resistance_damage:
        stats_lines.append(
            fmt(
                emojis.explosive_resistance_damage,
                item_stats.explosive_resistance_damage,
                ItemStat.explosive_resistance_damage,
            )
        )
    if item_stats.walk:
        stats_lines.append(fmt(emojis.walk, item_stats.walk, ItemStat.walk))
    if item_stats.jump:
        stats_lines.append(fmt(emojis.jump, item_stats.jump, ItemStat.jump))
    if item_stats.range:
        stats_lines.append(
            fmt(
                emojis.range,
                format_range(item_stats.range, item_stats.range_addon),
                ItemStat.range,
            )
        )
    if item_stats.push:
        count = 1 if item_stats.push > MAX_EMOJIS else item_stats.push
        stats_lines.append(fmt(emojis.push * count, item_stats.push, ItemStat.push))
    if item_stats.pull:
        count = 1 if item_stats.pull > MAX_EMOJIS else item_stats.pull
        stats_lines.append(fmt(emojis.pull * count, item_stats.pull, ItemStat.pull))
    if item_stats.recoil:
        stats_lines.append(fmt(emojis.recoil, item_stats.recoil, ItemStat.recoil))
    if item_stats.advance:
        count = 1 if item_stats.advance > MAX_EMOJIS else item_stats.advance
        stats_lines.append(fmt(emojis.advance * count, item_stats.advance, ItemStat.advance))
    if item_stats.retreat:
        count = 1 if item_stats.retreat > MAX_EMOJIS else item_stats.retreat
        stats_lines.append(fmt(emojis.retreat * count, item_stats.retreat, ItemStat.retreat))
    if item_stats.repair:
        stats_lines.append(fmt(emojis.repair, item_stats.repair, ItemStat.repair))

    if item_stats.uses:
        count = 1 if item_stats.uses > MAX_EMOJIS else item_stats.uses
        costs_lines.append(fmt(emojis.uses * count, item_stats.uses, ItemStat.uses))
    if item_stats.backfire:
        costs_lines.append(fmt(emojis.backfire, item_stats.backfire, ItemStat.backfire))
    if item_stats.heat_generation:
        costs_lines.append(
            fmt(emojis.heat_generation, item_stats.heat_generation, ItemStat.heat_generation)
        )
    if item_stats.energy_cost:
        costs_lines.append(fmt(emojis.energy_cost, item_stats.energy_cost, ItemStat.energy_cost))
    if item_stats.bullets_cost:
        costs_lines.append(fmt(emojis.bullets_cost, item_stats.bullets_cost, ItemStat.bullets_cost))
    if item_stats.rockets_cost:
        costs_lines.append(fmt(emojis.rockets_cost, item_stats.rockets_cost, ItemStat.rockets_cost))
    if item_stats.advance or item_stats.retreat:
        # if item has no costs, don't put jump-required separately
        (costs_lines or stats_lines).append(
            f"{emojis.jump} **{gettext('item-lookup-jump-required')}**"
        )
    # TODO: shield stats
    # TODO: POWER_KIT boost_power
    return stats_lines, costs_lines
