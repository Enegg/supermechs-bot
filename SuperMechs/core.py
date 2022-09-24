from __future__ import annotations

import typing as t
from json import load

from attrs import Factory, define, frozen
from typing_extensions import Self

from .enums import Rarity
from .game_types import AnyMechStats, AnyStatKey, AnyStats, StatDict
from .utils import MISSING, dict_items_as

# order reference
WORKSHOP_STATS = tuple(AnyMechStats.__annotations__)

# this is offset by 1 as items start at lvl 1
MAX_LVL_FOR_TIER = {tier: level for tier, level in zip(Rarity, range(9, 50, 10))} | {Rarity.D: 0}


class Name(t.NamedTuple):
    default: str
    in_game: str = MISSING
    short: str = MISSING

    def __str__(self) -> str:
        return self.default

    def __format__(self, __format_spec: str, /) -> str:
        return self.default.__format__(__format_spec)

    @property
    def game_name(self) -> str:
        return self.default if self.in_game is MISSING else self.in_game

    @property
    def short_name(self) -> str:
        if self.short is not MISSING:
            return self.short

        return self.default if len(self.default) <= len(self.game_name) else self.game_name


class Stat(t.NamedTuple):
    key: str
    name: Name
    emoji: str = "❔"
    beneficial: bool = True
    buff: t.Literal["+", "+%", "-%", "+2%"] | None = None

    def __str__(self) -> str:
        return self.name.default

    @classmethod
    def from_dict(cls, json: StatDict, key: str) -> Self:
        return cls(
            key=key,
            name=Name(**json["names"]),
            emoji=json.get("emoji", "❔"),
            beneficial=json.get("beneficial", True),
            buff=json.get("buff", None),
        )


def _load_stats():
    with open("SuperMechs/static/StatData.json") as file:
        json: dict[AnyStatKey, StatDict] = load(file)
        return {stat_key: Stat.from_dict(value, stat_key) for stat_key, value in json.items()}


STATS = _load_stats()


@frozen
class TransformRange:
    """Represents a range of transformation tiers an item can have."""

    range: range

    def __str__(self) -> str:
        return "".join(rarity.emoji for rarity in self)

    def __iter__(self) -> t.Iterator[Rarity]:
        return (Rarity.__call__(n) for n in self.range)

    def __len__(self) -> int:
        return len(self.range)

    def __contains__(self, item: Rarity | TransformRange) -> bool:
        match item:
            case Rarity():
                return item.level in self.range

            case TransformRange():
                return item.range in self.range

            case _:
                return NotImplemented

    @property
    def min(self) -> Rarity:
        """Lower range bound"""
        return Rarity.__call__(self.range.start)

    @property
    def max(self) -> Rarity:
        """Upper range bound"""
        return Rarity.__call__(self.range.stop - 1)

    def is_single_tier(self) -> bool:
        """Whether range has only one rarity"""
        return len(self.range) == 1

    @classmethod
    def from_rarity(cls, lower: Rarity | int, upper: Rarity | int | None = None) -> Self:
        """Construct a TransformRange object from upper and lower bounds.
        Unlike `range` object, upper bound is inclusive."""

        if isinstance(lower, int):
            lower = Rarity.__call__(lower)

        if upper is None:
            upper = lower

        elif isinstance(upper, int):
            upper = Rarity.__call__(upper)

        if not Rarity.C <= lower <= upper:
            if lower > upper:
                raise ValueError("upper rarity below lower rarity")

            raise ValueError("rarities out of bounds")

        return cls(range(lower.level, upper.level + 1))

    @classmethod
    def from_string(cls, string: str, /) -> Self:
        """Construct a TransformRange object from a string like "C-E" or "M"."""
        up, _, down = string.strip().partition("-")

        if down:
            return cls.from_rarity(Rarity[up.upper()], Rarity[down.upper()])

        return cls.from_rarity(Rarity[up.upper()])

    def next_tier(self, current: Rarity, /) -> Rarity:
        if current >= self.max:
            raise ValueError("Highest rarity already achieved")

        return Rarity.__call__(current.level + 1)


class GameVars(t.NamedTuple):
    MAX_WEIGHT: int = 1000
    OVERWEIGHT: int = 10
    PENALTIES: AnyMechStats = {"health": 15}

    @property
    def MAX_OVERWEIGHT(self) -> int:
        return self.MAX_WEIGHT + self.OVERWEIGHT

    @staticmethod
    def default() -> GameVars:
        return DEFAULT_VARS


DEFAULT_VARS = GameVars()


@define
class ArenaBuffs:
    BASE_PERCENT: t.ClassVar = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20)
    HP_INCREASES: t.ClassVar = (0, +10, +30, +60, 90, 120, 150, 180, +220, +260, 300, 350)
    # fmt: off
    BUFFABLE_STATS: t.ClassVar = (
        "eneCap", "eneReg", "eneDmg", "heaCap", "heaCol", "heaDmg", "phyDmg",
        "expDmg", "eleDmg", "phyRes", "expRes", "eleRes", "health", "backfire"
    )
    # XXX: perhaps include +% titan damage?
    # fmt: on
    levels: dict[str, int] = Factory(lambda: dict.fromkeys(ArenaBuffs.BUFFABLE_STATS, 0))

    def __getitem__(self, item: str) -> int:
        return self.levels[item]

    def is_at_zero(self) -> bool:
        """Whether all buffs are at level 0"""
        return all(v == 0 for v in self.levels.values())

    def total_buff(self, stat_name: str, value: int) -> int:
        """Buffs a value according to given stat."""
        if stat_name not in self.levels:
            return value

        level = self.levels[stat_name]

        if stat_name == "health":
            return value + self.HP_INCREASES[level]

        return round(value * (1 + self.get_percent(stat_name, level) / 100))

    def total_buff_difference(self, stat_name: str, value: int) -> tuple[int, int]:
        """Returns buffed value and the difference between the result and the initial value."""
        buffed = self.total_buff(stat_name, value)
        return buffed, buffed - value

    @classmethod
    def get_percent(cls, stat_name: str, level: int) -> int:
        """Returns an int representing the precentage for the stat's increase."""

        match STATS[stat_name].buff:
            case "+%":
                return cls.BASE_PERCENT[level]

            case "+2%":
                return cls.BASE_PERCENT[level] * 2

            case "-%":
                return -cls.BASE_PERCENT[level]

            case "+":
                raise TypeError(f"Stat {stat_name!r} has absolute increase")

            case None:
                raise ValueError(f"Stat {stat_name!r} has no buffs associated")

    @classmethod
    def buff_as_str(cls, stat_name: str, level: int) -> str:
        """Returns a formatted string representation of the stat's value at the given level."""
        if stat_name == "health":
            return f"+{cls.HP_INCREASES[level]}"

        return f"{cls.get_percent(stat_name, level):+}%"

    def buff_as_str_aware(self, stat: str) -> str:
        """Returns a formatted string representation of the stat's value."""
        return self.buff_as_str(stat, self.levels[stat])

    @classmethod
    def iter_as_str(cls, stat_name: str) -> t.Iterator[str]:
        levels = len(cls.HP_INCREASES) if stat_name == "health" else len(cls.BASE_PERCENT)

        for n in range(levels):
            yield cls.buff_as_str(stat_name, n)

    @classmethod
    def maxed(cls) -> Self:
        """Returns an ArenaBuffs object with all levels maxed."""

        levels = dict.fromkeys(cls.BUFFABLE_STATS, len(cls.BASE_PERCENT) - 1)
        levels["health"] = len(cls.HP_INCREASES) - 1
        max_buffs = cls(levels)

        setattr(cls, "maxed", staticmethod(lambda: max_buffs))

        return max_buffs

    def buff_stats(self, stats: AnyStats, /, *, buff_health: bool = False) -> AnyStats:
        """Returns the buffed stats."""
        buffed: AnyStats = {}

        for key, value in dict_items_as(int | list[int], stats):
            if key == "health" and not buff_health:
                assert type(value) is int
                buffed[key] = value

            elif isinstance(value, list):
                buffed[key] = [self.total_buff(key, v) for v in value]

            else:
                value = self.total_buff(key, value)
                buffed[key] = value

        return buffed


MAX_BUFFS = ArenaBuffs.maxed()


def abbreviate_names(names: t.Iterable[str], /) -> dict[str, set[str]]:
    """Returns dict of abbrevs:
    Energy Free Armor => EFA"""
    abbrevs: dict[str, set[str]] = {}

    for name in names:
        if len(name) < 8:
            continue

        is_single_word = " " not in name

        if (IsNotPascal := not name.isupper() and name[1:].islower()) and is_single_word:
            continue

        abbrev = {"".join(a for a in name if a.isupper()).lower()}

        if not is_single_word:
            abbrev.add(name.replace(" ", "").lower())  # Fire Fly => firefly

        if not IsNotPascal and is_single_word:  # takes care of PascalCase names
            last = 0
            for i, a in enumerate(name):
                if a.isupper():
                    if string := name[last:i].lower():
                        abbrev.add(string)

                    last = i

            abbrev.add(name[last:].lower())

        for abb in abbrev:
            abbrevs.setdefault(abb, {name}).add(name)

    return abbrevs
