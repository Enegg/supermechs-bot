import math
from collections import abc
from functools import partial
from itertools import islice

from app.bridges.sm_utils import acronym_of
from app.text_utils import Char

from supermechs.abc.stats import StatsMapping, StatType
from supermechs.all import Stat


def format_float(num: float, decimals: int) -> str:
    num = round(float(num), decimals)

    if num.is_integer():
        return f"{num:.0f}"

    return f"{num:.{decimals}f}"


def try_shorten(name: str, limit: int = 16) -> str:
    if len(name) < limit:
        return name

    if (acronym := acronym_of(name)) is not None:
        return acronym

    return name[: limit - 1] + Char.TRIPLE_DOT


def compare_numbers(
    x: StatType, y: StatType, lower_is_better: bool = False
) -> tuple[StatType, StatType]:
    return (x - y, 0) if lower_is_better ^ (x > y) else (0, y - x)


def get_row_width(size: int, max_length: int) -> int:
    """Return the length `l` of slices a sequence of given `size` can be partitioned into.

    `max_length` determines the upper bound for `l`, however `l` is determined in a way
    such that the final slice has at least `l // 2 + 1` length.
    """
    if size < max_length:
        return size
    for n in range(max_length, 2, -1):
        rem = size % n
        if rem == 0 or rem >= n - 1:
            return n
    return max_length


def mean_and_deviation(a: float, b: float) -> tuple[float, float]:
    mean = (a + b) / 2
    deviation = math.sqrt(((a - mean) ** 2 + (b - mean) ** 2) / 2)
    return mean, deviation


def format_average(a: float, b: float, decimals: int = 1) -> str:
    mean, deviation = mean_and_deviation(a, b)
    dev = deviation / mean * 100
    str_mean = format_float(mean, 1)
    str_dev = format_float(dev, decimals)
    return f"{str_mean} ±{str_dev}%"


def _format_single(
    stats: StatsMapping, selectors: abc.Iterable[Stat]
) -> abc.Iterator[tuple[Stat, str]]:
    for stat in selectors:
        if value := stats.get(stat, 0):
            yield (stat, str(value))


def _format_double(
    stats: StatsMapping,
    format_: abc.Callable[[float, float], str],
    main_stat: Stat,
    addon_stat: Stat,
) -> abc.Iterator[tuple[Stat, str]]:
    if value := stats.get(main_stat, 0):
        if (value2 := stats.get(addon_stat, value)) != value:
            yield (main_stat, format_(value, value2))

        else:
            yield (main_stat, str(value))


def iter_formatted_stats(
    stats: StatsMapping, avg: bool, decimals: int = 1
) -> abc.Iterator[tuple[Stat, str]]:
    def format_two(a: float, b: float) -> str:
        return f"{a}-{b}"

    format_: abc.Callable[[float, float], str] = (
        partial(format_average, decimals=decimals) if avg else format_two
    )

    yield from _format_single(stats, islice(Stat, 11))
    yield from _format_double(stats, format_, Stat.physical_damage, Stat.physical_damage_addon)
    yield from _format_single(stats, (Stat.physical_resistance_damage,))
    yield from _format_double(stats, format_, Stat.electric_damage, Stat.electric_damage_addon)
    yield from _format_single(
        stats,
        (
            Stat.energy_damage,
            Stat.energy_capacity_damage,
            Stat.regeneration_damage,
            Stat.electric_resistance_damage,
        ),
    )
    yield from _format_double(stats, format_, Stat.explosive_damage, Stat.explosive_damage_addon)
    yield from _format_single(
        stats,
        (
            Stat.heat_damage,
            Stat.heat_capacity_damage,
            Stat.cooling_damage,
            Stat.explosive_resistance_damage,
            Stat.walk,
            Stat.jump,
        ),
    )
    yield from _format_double(stats, format_two, Stat.range, Stat.range_addon)
    yield from _format_single(
        stats,
        (
            Stat.push,
            Stat.pull,
            Stat.recoil,
            Stat.advance,
            Stat.retreat,
            Stat.uses,
            Stat.backfire,
            Stat.heat_generation,
            Stat.energy_cost,
            Stat.bullets_cost,
            Stat.rockets_cost,
        ),
    )
