import math
from collections import abc

from app import i18n
from app.assets import EMOJIS
from app.utils import StringBuilder

import supermechs.all as sm
from supermechs.enums import ItemStat

MAX_EMOJIS = 4
"""Threshold for multiple emojis shown inline in the stats field."""


def format_real(num: int | float, decimals: int) -> str:
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
    str_mean = format_real(mean, 1)
    str_dev = format_real(dev, decimals)
    return f"{str_mean} ±{str_dev}%"


def format_range(lo: int, hi: int, /) -> str:
    if hi <= 0:
        return f"{lo}+"

    if lo == hi:
        return str(lo)

    return f"{lo}-{hi}"


def format_range_display(item: sm.Item, stats: sm.ItemStats, /) -> str:
    ARENA_SIZE = 10
    # since your mech always occupes one spot in the arena, the range is N-1
    MAX_RANGE = ARENA_SIZE - 1
    # if we have space for it, add some padding for clarity
    PADDING = 2

    damage_emoji = EMOJIS.get_element(item.element).mention
    empty_emoji = EMOJIS.arena_position_empty.mention

    lo = stats.range_min - 1
    hi = MAX_RANGE if stats.range_max <= 0 else stats.range_max

    # ... <dmg> <slot> <dmg> ...
    if item.slot_id is sm.Item.Slot.teleport and hi <= MAX_RANGE // 2:
        r = hi - lo
        return (
            StringBuilder()
            .add_repeated(empty_emoji, PADDING)
            .add_repeated(damage_emoji, r)
            .add(EMOJIS.item_slot_teleport.mention)
            .add_repeated(damage_emoji, r)
            .add_repeated(empty_emoji, PADDING)
            .build()
        )

    # <retreat/recoil> ... <slot> ... <advance> ... <dmg> ... <end>
    range_display = StringBuilder()
    if stats.retreat != 0:
        range_display.add(EMOJIS.stat_retreat.mention).add_repeated(empty_emoji, stats.retreat - 1)
    elif stats.recoil != 0:
        range_display.add(EMOJIS.stat_recoil.mention).add_repeated(empty_emoji, stats.recoil - 1)

    range_display.add(EMOJIS.get_item_slot(item.slot_id).mention)
    # if advance would appear after beginning of damage range, don't show it
    if stats.advance != 0 and stats.advance < stats.range_min:
        range_display.add_repeated(empty_emoji, stats.advance - 1).add(EMOJIS.stat_advance.mention)
    (
        range_display
        .add_repeated(empty_emoji, lo - stats.advance if stats.advance < stats.range_min else lo)
        .add_repeated(damage_emoji, hi - lo)
    )  # fmt: skip
    width = (stats.retreat or stats.recoil) + max(hi, stats.advance)
    if width > ARENA_SIZE // 2:
        (
            range_display
            .add_repeated(empty_emoji, MAX_RANGE - width)
            .add(EMOJIS.arena_position_corner.mention)
        )  # fmt: skip
    else:
        range_display.add_repeated(empty_emoji, PADDING)

    return range_display.build()


def item_transform_range(item: sm.Item, /, stage_index: int = -1) -> str:
    str_range: list[str] = [str(EMOJIS.get_tier(stage.tier, hollow=True)) for stage in item.stages]
    str_range[stage_index] = str(EMOJIS.get_tier(item.stages[stage_index].tier))
    return "".join(str_range)


def has_damage_spread(stats: sm.ItemStats, /) -> bool:
    return (
        stats.physical_damage_min != stats.physical_damage_max
        or stats.explosive_damage_min != stats.explosive_damage_max
        or stats.electric_damage_min != stats.electric_damage_max
    )


def has_damage(stats: sm.ItemStats, /) -> bool:
    return (
        stats.physical_damage_min != 0
        or stats.explosive_damage_min != 0
        or stats.electric_damage_min != 0
    )


def has_buff_affected_stats(stats: sm.ItemStats, /) -> bool:
    return (
        stats.energy_capacity != 0
        or stats.energy_regeneration != 0
        or stats.energy_damage != 0
        or stats.heat_capacity != 0
        or stats.heat_cooling != 0
        or stats.heat_damage != 0
        or stats.physical_damage_min != 0
        or stats.explosive_damage_min != 0
        or stats.electric_damage_min != 0
        or stats.physical_resistance != 0
        or stats.explosive_resistance != 0
        or stats.electric_resistance != 0
        or stats.backfire != 0
    )


def format_stats(
    item: sm.Item, item_stats: sm.ItemStats, gettext: i18n.GetText, *, avg: bool
) -> tuple[list[str], list[str]]:
    def fmte(emoji: str, value: int | str, stat_key: ItemStat, /) -> str:
        return f"{emoji} **{value}** {gettext.get_stat_name(stat_key)}"

    def fmt(value: int | str, stat_key: ItemStat, /) -> str:
        return fmte(EMOJIS.get_stat(stat_key).mention, value, stat_key)

    format_damage: abc.Callable[[int, int], str] = (
        format_damage_average if avg else format_damage_default
    )

    stats_lines: list[str] = []
    costs_lines: list[str] = []

    if item_stats.weight:
        stats_lines.append(fmt(item_stats.weight, ItemStat.weight))
    if item_stats.hit_points:
        stats_lines.append(fmt(item_stats.hit_points, ItemStat.hit_points))
    if item_stats.energy_capacity:
        stats_lines.append(fmt(item_stats.energy_capacity, ItemStat.energy_capacity))
    if item_stats.energy_regeneration:
        stats_lines.append(fmt(item_stats.energy_regeneration, ItemStat.energy_regeneration))
    if item_stats.heat_capacity:
        stats_lines.append(fmt(item_stats.heat_capacity, ItemStat.heat_capacity))
    if item_stats.heat_cooling:
        stats_lines.append(fmt(item_stats.heat_cooling, ItemStat.heat_cooling))
    if item_stats.physical_resistance:
        stats_lines.append(fmt(item_stats.physical_resistance, ItemStat.physical_resistance))
    if item_stats.explosive_resistance:
        stats_lines.append(fmt(item_stats.explosive_resistance, ItemStat.explosive_resistance))
    if item_stats.electric_resistance:
        stats_lines.append(fmt(item_stats.electric_resistance, ItemStat.electric_resistance))
    if item_stats.bullets_capacity:
        stats_lines.append(fmt(item_stats.bullets_capacity, ItemStat.bullets_capacity))
    if item_stats.rockets_capacity:
        stats_lines.append(fmt(item_stats.rockets_capacity, ItemStat.rockets_capacity))
    if item_stats.physical_damage_min:
        stats_lines.append(
            fmt(
                format_damage(item_stats.physical_damage_min, item_stats.physical_damage_max),
                ItemStat.physical_damage,
            )
        )
    if item_stats.physical_resistance_damage:
        stats_lines.append(
            fmt(item_stats.physical_resistance_damage, ItemStat.physical_resistance_damage)
        )
    if item_stats.electric_damage_min:
        stats_lines.append(
            fmt(
                format_damage(item_stats.electric_damage_min, item_stats.electric_damage_max),
                ItemStat.electric_damage,
            )
        )
    if item_stats.energy_damage:
        stats_lines.append(fmt(item_stats.energy_damage, ItemStat.energy_damage))
    if item_stats.energy_capacity_damage:
        stats_lines.append(fmt(item_stats.energy_capacity_damage, ItemStat.energy_capacity_damage))
    if item_stats.regeneration_damage:
        stats_lines.append(fmt(item_stats.regeneration_damage, ItemStat.regeneration_damage))
    if item_stats.electric_resistance_damage:
        stats_lines.append(
            fmt(item_stats.electric_resistance_damage, ItemStat.electric_resistance_damage)
        )
    if item_stats.explosive_damage_min:
        stats_lines.append(
            fmt(
                format_damage(item_stats.explosive_damage_min, item_stats.explosive_damage_max),
                ItemStat.explosive_damage,
            )
        )
    if item_stats.heat_damage:
        stats_lines.append(fmt(item_stats.heat_damage, ItemStat.heat_damage))
    if item_stats.heat_capacity_damage:
        stats_lines.append(fmt(item_stats.heat_capacity_damage, ItemStat.heat_capacity_damage))
    if item_stats.cooling_damage:
        stats_lines.append(fmt(item_stats.cooling_damage, ItemStat.cooling_damage))
    if item_stats.explosive_resistance_damage:
        stats_lines.append(
            fmt(item_stats.explosive_resistance_damage, ItemStat.explosive_resistance_damage)
        )
    if item_stats.walk:
        stats_lines.append(fmt(item_stats.walk, ItemStat.walk))
    if item_stats.jump:
        stats_lines.append(fmt(item_stats.jump, ItemStat.jump))
    if item_stats.range_min:
        stats_lines.append(
            fmt(format_range(item_stats.range_min, item_stats.range_max), ItemStat.range)
        )
    if item_stats.push:
        count = 1 if item_stats.push > MAX_EMOJIS else item_stats.push
        stats_lines.append(fmte(str(EMOJIS.stat_push) * count, item_stats.push, ItemStat.push))
    if item_stats.pull:
        count = 1 if item_stats.pull > MAX_EMOJIS else item_stats.pull
        stats_lines.append(fmte(str(EMOJIS.stat_pull) * count, item_stats.pull, ItemStat.pull))
    if item_stats.recoil:
        stats_lines.append(fmt(item_stats.recoil, ItemStat.recoil))
    if item_stats.advance:
        stats_lines.append(fmt(item_stats.advance, ItemStat.advance))
    if item_stats.retreat:
        stats_lines.append(fmt(item_stats.retreat, ItemStat.retreat))
    if item_stats.range_min or item_stats.retreat:
        stats_lines.append(format_range_display(item, item_stats))
    if item_stats.repair:
        stats_lines.append(fmt(item_stats.repair, ItemStat.repair))
    if item_stats.block_percentage:
        stats_lines.append(
            fmte(
                str(EMOJIS.stat_block_percentage),
                f"{item_stats.block_percentage}%",
                ItemStat.block_percentage,
            )
        )
    if item_stats.heat_per_block and item_stats.hit_points_per_block:
        stats_lines.append(
            f"{EMOJIS.stat_heat_generation} **{item_stats.heat_per_block}** Heat per {EMOJIS.stat_hit_points} **{item_stats.hit_points_per_block}** damage blocked"
        )
    if item_stats.energy_per_block and item_stats.hit_points_per_block:
        stats_lines.append(
            f"{EMOJIS.stat_energy_cost} **{item_stats.energy_per_block}** Energy per {EMOJIS.stat_hit_points} **{item_stats.hit_points_per_block}** damage blocked"
        )

    if item_stats.uses:
        count = 1 if item_stats.uses > MAX_EMOJIS else item_stats.uses
        costs_lines.append(fmte(str(EMOJIS.stat_uses) * count, item_stats.uses, ItemStat.uses))
    if item_stats.backfire:
        costs_lines.append(fmt(item_stats.backfire, ItemStat.backfire))
    if item_stats.heat_generation:
        costs_lines.append(fmt(item_stats.heat_generation, ItemStat.heat_generation))
    if item_stats.energy_cost:
        costs_lines.append(fmt(item_stats.energy_cost, ItemStat.energy_cost))
    if item_stats.bullets_cost:
        costs_lines.append(fmt(item_stats.bullets_cost, ItemStat.bullets_cost))
    if item_stats.rockets_cost:
        costs_lines.append(fmt(item_stats.rockets_cost, ItemStat.rockets_cost))
    if item_stats.advance or item_stats.retreat:
        # if item has no costs, don't put jump-required separately
        (costs_lines or stats_lines).append(
            f"{EMOJIS.stat_jump} **{gettext('item-lookup-jump-required')}**"
        )
    return stats_lines, costs_lines


# https://en.wikipedia.org/wiki/Metric_prefix
_SUFFIXES = ("", "k", "M", "G", "T")
# abbreviate at 5+ digits
METRIC_FORMAT_THRESHOLD = 1e4


def format_real_to_metric(n: int | float, /) -> str:
    """Format a number with a k/M/… metric suffix for `abs(n) >= 1e4`.

    >>> format_large_number(-9999)
    "-9,999"
    >>> format_large_number(10_000)
    "10k"
    >>> format_large_number(1.2e6)
    "1.2M"
    """
    if abs(n) < METRIC_FORMAT_THRESHOLD:
        return f"{n:,}"

    exp = math.floor(math.log(abs(n), 1e3))
    exp = min(exp, len(_SUFFIXES) - 1)
    return format_real(n / math.pow(1e3, exp), 1) + _SUFFIXES[exp]
