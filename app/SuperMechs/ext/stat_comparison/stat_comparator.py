import statistics
import typing as t

from typeshed import KT, VT, twotuple

from SuperMechs.api import STATS, AnyStats, Element, Stat, ValueRange
from SuperMechs.core import Names

custom_stats: dict[str, Stat] = {
    "spread": Stat("spread", Names("Damage spread"), "🎲", False),
    "anyDmg": Stat("anyDmg", Names("Damage"), Element.COMBINED.emoji),
    "totalDmg": Stat("totalDmg", Names("Damage potential"), "🎯"),
}
STAT_KEY_ORDER = tuple(STATS)


class ComparisonContext(t.NamedTuple):
    coerce_damage_types: bool = False
    damage_average: bool = False
    damage_spread: bool = False
    damage_potential: bool = False


class Comparator:
    """Class responsible for comparing a set of values and producing
    a human comprehensible representation.
    """

    pass


class ComparisonResult:
    """Who knows"""


class Display:
    """Simple-minded object responsible for providing context for formatting."""


@t.overload
def compare_numbers(x: int, y: int, lower_is_better: bool = False) -> twotuple[int]:
    ...


@t.overload
def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    ...


def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    return (x - y, 0) if lower_is_better ^ (x > y) else (0, y - x)


def compare_integers(stat: Stat, number1: int, number2: int):
    pass


def compare_value_ranges(stat: Stat, range1: ValueRange, range2: ValueRange):
    pass


def comparator(
    stats_a: AnyStats, stats_b: AnyStats
) -> t.Iterator[tuple[Stat,]]:
    for stat_name, stat in STATS.items():
        match stats_a.get(stat_name), stats_b.get(stat_name):
            case None, None:
                continue

            case int() as number1, int() as number2:
                compare_integers(stat, number1, number2)

            case (int() as number1, None as number2) | (None as number1, int() as number2):
                pass

            case ValueRange() as range1, ValueRange() as range2:
                compare_value_ranges(stat, range1, range2)

            case (ValueRange() as range1, None as range2) | (
                None as range1,
                ValueRange() as range2,
            ):
                pass

            case value_a, value_b:
                raise TypeError(f"Unknown values: {value_a!r:.20}, {value_b!r:.20}")

        yield stat,
