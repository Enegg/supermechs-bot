import math
import typing
from collections import abc
from functools import partial
from itertools import islice

from typeshed import twotuple

from supermechs.abc.stats import StatsMapping
from supermechs.api import Stat


def truncate_float(num: float, decimals: int) -> tuple[float, int]:
    num = round(num, decimals)
    if float(num).is_integer():  # ints don't have .is_integer
        return num, 0
    return num, decimals


def format_float(num: float, decimals: int) -> str:
    num, decimals = truncate_float(num, decimals)
    return f"{num:.{decimals}f}"


def try_shorten(name: str, limit: int = 16) -> str:
    if len(name) < limit:
        return name

    return "".join(s for s in name if s.isupper())


@typing.overload
def compare_numbers(x: int, y: int, lower_is_better: bool = False) -> twotuple[int]:
    ...


@typing.overload
def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    ...


def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    return (x - y, 0) if lower_is_better ^ (x > y) else (0, y - x)


def wrap_nicely(size: int, max_length: int) -> int:
    """Returns the length `l` of slices a sequence of given `size` can be partitioned into.

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
    return f"x̄{str_mean} ±{str_dev}%"


def iter_formatted_stats(
    stats: StatsMapping, avg: bool, decimals: int = 1
) -> abc.Iterator[tuple[Stat, str]]:
    format_: abc.Callable[[float, float], str] = (
        partial(format_average, decimals=decimals) if avg else lambda a, b: f"{a}-{b}"
    )

    for stat in islice(Stat, 11):
        if value := stats.get(stat, 0):
            yield (stat, str(value))

    if value := stats.get(Stat.physical_damage, 0):
        stat = Stat.physical_damage
        if (value2 := stats.get(Stat.physical_damage_addon, value)) != value:
            yield (stat, format_(value, value2))

        else:
            yield (stat, str(value))

    if value := stats.get(Stat.physical_resistance_damage, 0):
        yield (Stat.physical_resistance_damage, str(value))

    if value := stats.get(Stat.electric_damage, 0):
        stat = Stat.electric_damage
        if (value2 := stats.get(Stat.electric_damage_addon, value)) != value:
            yield (stat, format_(value, value2))

        else:
            yield (stat, str(value))

    for stat in (
        Stat.energy_damage,
        Stat.energy_capacity_damage,
        Stat.regeneration_damage,
        Stat.electric_resistance_damage,
    ):
        if value := stats.get(stat, 0):
            yield (stat, str(value))

    if value := stats.get(Stat.explosive_damage, 0):
        stat = Stat.explosive_damage
        if (value2 := stats.get(Stat.explosive_damage_addon, value)) != value:
            yield (stat, format_(value, value2))

        else:
            yield (stat, str(value))

    for stat in (
        Stat.heat_damage,
        Stat.heat_capacity_damage,
        Stat.cooling_damage,
        Stat.explosive_resistance_damage,
        Stat.walk,
        Stat.jump,
    ):
        if value := stats.get(stat, 0):
            yield (stat, str(value))

    if value := stats.get(Stat.range, 0):
        stat = Stat.range
        if (value2 := stats.get(Stat.range_addon, value)) != value:
            yield (stat, f"{value}-{value2}")

        else:
            yield (Stat.range, str(value))

    for stat in (
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
    ):
        if value := stats.get(stat, 0):
            yield (stat, str(value))
