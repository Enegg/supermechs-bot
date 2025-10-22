import math

from app.assets import EMOJIS
from app.text_utils import Char, acronym_of

import dupermechs.all as sm


def format_float(num: float, decimals: int) -> str:
    num = round(float(num), decimals)

    if num.is_integer():
        return f"{num:.0f}"

    return f"{num:.{decimals}f}"


def try_shorten(name: str, limit: int = 16) -> str:
    if len(name) <= limit:
        return name

    if (acronym := acronym_of(name)) is not None and len(acronym) <= limit:
        return acronym

    return name[: limit - 1] + Char.TRIPLE_DOT


def format_damage_default(lo: int, hi: int, /) -> str:
    if hi and lo != hi:
        return f"{lo}-{hi}"

    return str(lo)


def mean_and_deviation(a: int | float, b: int | float, /) -> tuple[float, float]:
    mean = (a + b) / 2
    deviation = math.sqrt(((a - mean) ** 2 + (b - mean) ** 2) / 2)
    return mean, deviation


def format_damage_average(lo: int | float, hi: int | float, /, *, decimals: int = 1) -> str:
    mean, deviation = mean_and_deviation(lo, hi)
    dev = deviation / mean * 100.0
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
