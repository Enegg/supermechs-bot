from __future__ import annotations

import typing as t
from json import load
from pathlib import Path

from attrs import Factory, define, frozen
from typing_extensions import Self

from .enums import Tier
from .typedefs import AnyMechStatKey, AnyStatKey, Name, StatDict
from .utils import MISSING

ValueT = t.TypeVar("ValueT", int, "ValueRange")

WORKSHOP_STATS: tuple[str, ...] = t.get_args(AnyMechStatKey)
"""The stats that can appear in mech summary, in order."""

MAX_LVL_FOR_TIER = {tier: level for tier, level in zip(Tier, range(9, 50, 10))} | {Tier.DIVINE: 0}
"""A mapping of a tier to the maximum level an item can have at this tier.
    Note that in game levels start at 1."""


class Names(t.NamedTuple):
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
    name: Names
    emoji: str = "❔"
    beneficial: bool = True
    buff: t.Literal["+", "+%", "-%", "+2%"] | None = None

    def __str__(self) -> str:
        return self.name.default

    @classmethod
    def from_dict(cls, json: StatDict, key: str) -> Self:
        return cls(
            key=key,
            name=Names(**json["names"]),
            emoji=json.get("emoji", "❔"),
            beneficial=json.get("beneficial", True),
            buff=json.get("buff", None),
        )


def _load_stats():
    with open(Path(__file__).parent / "static/StatData.json") as file:
        json: dict[AnyStatKey, StatDict] = load(file)
        return {stat_key: Stat.from_dict(value, stat_key) for stat_key, value in json.items()}


STATS = _load_stats()


@frozen
class TransformRange:
    """Represents a range of transformation tiers an item can have."""

    range: range

    def __str__(self) -> str:
        return "".join(rarity.emoji for rarity in self)

    def __iter__(self) -> t.Iterator[Tier]:
        return map(Tier.__call__, self.range)

    def __len__(self) -> int:
        return len(self.range)

    def __contains__(self, item: Tier | TransformRange) -> bool:
        if isinstance(item, Tier):
            return item.level in self.range

        if isinstance(item, type(self)):
            return item.range in self.range

        return NotImplemented

    @property
    def min(self) -> Tier:
        """Lower range bound."""
        return Tier.__call__(self.range.start)

    @property
    def max(self) -> Tier:
        """Upper range bound."""
        return Tier.__call__(self.range.stop - 1)

    def is_single_tier(self) -> bool:
        """Whether range has only one tier."""
        return len(self.range) == 1

    def as_tier_str(self, level: int = -1, chars: str | tuple[str, str] = "()") -> str:
        s = ""
        if level == -1:
            level = len(self) - 1
        for i, rarity in enumerate(self):
            if i == level:
                s += f"{chars[0]}{rarity.emoji}{chars[-1]}"
                continue
            s += rarity.emoji
        return s

    @classmethod
    def from_tiers(cls, lower: Tier | int, upper: Tier | int | None = None) -> Self:
        """Construct a TransformRange object from upper and lower bounds.
        Unlike `range` object, upper bound is inclusive."""

        if isinstance(lower, int):
            lower = Tier.__call__(lower)

        if upper is None:
            upper = lower

        elif isinstance(upper, int):
            upper = Tier.__call__(upper)

        if lower > upper:
            raise ValueError("Upper tier below lower tier")

        return cls(range(lower.level, upper.level + 1))

    @classmethod
    def from_string(cls, string: str, /) -> Self:
        """Construct a TransformRange object from a string like "C-E" or "M"."""
        up, _, down = string.strip().partition("-")

        if down:
            return cls.from_tiers(Tier.from_letter(up), Tier.from_letter(down))

        return cls.from_tiers(Tier.from_letter(up))


class GameVars(t.NamedTuple):
    MAX_WEIGHT: int = 1000
    OVERWEIGHT: int = 10
    PENALTIES: AnyMechStats = {"health": 15}
    EXCLUSIVE_STATS: frozenset[str] = frozenset(("phyRes", "expRes", "eleRes"))

    @property
    def MAX_OVERWEIGHT(self) -> int:
        return self.MAX_WEIGHT + self.OVERWEIGHT

    @classmethod
    def default(cls) -> Self:
        return DEFAULT_VARS


DEFAULT_VARS = GameVars()


class ValueRange(t.NamedTuple):
    """Lightweight tuple to represent a range of values."""

    lower: int
    upper: int

    def __str__(self) -> str:
        if self.is_single:  # this is false if either is NaN
            return str(self.lower)
        return f"{self.lower}-{self.upper}"

    def __format__(self, format_spec: str, /) -> str:
        # the general format to expect is "number_spec:separator"
        val_fmt, colon, sep = format_spec.partition(":")

        if not colon:
            sep = "-"

        if self.is_single:
            return format(self.lower, val_fmt)

        return f"{self.lower:{val_fmt}}{sep}{self.upper:{val_fmt}}"

    @property
    def is_single(self) -> bool:
        """Whether the range bounds are equal value."""
        return self.lower == self.upper

    @property
    def average(self) -> float:
        """Average of the value range."""
        if self.is_single:
            return self.lower
        return (self.lower + self.upper) / 2

    def __add__(self, value: tuple[int, int]) -> Self:
        return type(self)(self.lower + value[0], self.upper + value[1])

    def __mul__(self, value: int) -> Self:
        return type(self)(self.lower * value, self.upper * value)


class BuffModifier(t.NamedTuple):
    value: int
    percent: bool = True

    def __str__(self) -> str:
        if self.percent:
            return f"{self.value:+}%"

        return f"+{self.value}"

    def __int__(self) -> int:
        return self.value


class AnyMechStats(t.TypedDict, total=False):
    weight: int
    health: int
    eneCap: int
    eneReg: int
    heaCap: int
    heaCol: int
    phyRes: int
    expRes: int
    eleRes: int
    bulletsCap: int
    rocketsCap: int
    walk: int
    jump: int


class AnyStats(AnyMechStats, total=False):
    # stats sorted in order they appear in-game
    phyDmg: ValueRange
    phyResDmg: int
    eleDmg: ValueRange
    eneDmg: int
    eneCapDmg: int
    eneRegDmg: int
    eleResDmg: int
    expDmg: ValueRange
    heaDmg: int
    heaCapDmg: int
    heaColDmg: int
    expResDmg: int
    # walk, jump
    range: ValueRange
    push: int
    pull: int
    recoil: int
    advance: int
    retreat: int
    uses: int
    backfire: int
    heaCost: int
    eneCost: int
    bulletsCost: int
    rocketsCost: int


@define
class ArenaBuffs:
    BASE_PERCENT: t.ClassVar = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20)
    HP_INCREASES: t.ClassVar = (0, +10, +30, +60, 90, 120, 150, 180, +220, +260, 300, 350)
    # fmt: off
    BUFFABLE_STATS: t.ClassVar = (
        "eneCap", "eneReg", "eneDmg", "heaCap", "heaCol", "heaDmg", "phyDmg",
        "expDmg", "eleDmg", "phyRes", "expRes", "eleRes", "health", "backfire"
    )
    # TODO: perhaps include +% titan damage?
    # fmt: on
    levels: dict[str, int] = Factory(lambda: dict.fromkeys(ArenaBuffs.BUFFABLE_STATS, 0))

    def __getitem__(self, stat_name: str) -> int:
        return self.levels[stat_name]

    def __setitem__(self, stat_name: str, level: int) -> None:
        if level > (max_lvl := self.max_level_of(stat_name)):
            raise ValueError(f"The max level for {stat_name!r} is {max_lvl}, got {level}")

        self.levels[stat_name] = level

    def is_at_zero(self) -> bool:
        """Whether all buffs are at level 0."""
        return all(v == 0 for v in self.levels.values())

    def buff(self, stat_name: str, value: int, /) -> int:
        """Buffs a value according to given stat."""
        if stat_name not in self.levels:
            return value

        level = self.levels[stat_name]
        abs_or_percent_increase, is_percent = self.modifier_at(stat_name, level)

        if is_percent:
            return round(value * (1 + abs_or_percent_increase / 100))

        return value + abs_or_percent_increase

    def buff_damage_range(self, stat_name: str, value: ValueRange, /) -> ValueRange:
        """Buff a value range according to given stat."""
        if stat_name not in self.levels:
            return value

        level = self.levels[stat_name]
        increase, _ = self.modifier_at(stat_name, level)

        return ValueRange(
            round(value.lower * (1 + increase / 100)), round(value.upper * (1 + increase / 100))
        )

    def buff_with_difference(self, stat_name: str, value: int, /) -> tuple[int, int]:
        """Returns buffed value and the difference between the result and the initial value."""
        buffed = self.buff(stat_name, value)
        return buffed, buffed - value

    # the overloads are redundant, but TypedDict fallbacks to object as their value type
    # and that doesn't play well with typing
    @t.overload
    def buff_stats(self, stats: AnyStats, /, *, buff_health: bool = ...) -> AnyStats:
        ...

    @t.overload
    def buff_stats(
        self, stats: t.Mapping[str, ValueT], /, *, buff_health: bool = ...
    ) -> dict[str, ValueT]:
        ...

    def buff_stats(
        self, stats: t.Mapping[str, ValueT] | AnyStats, /, *, buff_health: bool = False
    ) -> dict[str, ValueT] | AnyStats:
        """Returns the buffed stats."""
        buffed: dict[str, ValueT] = {}

        for key, value in t.cast(t.Mapping[str, ValueT], stats).items():
            if key == "health" and not buff_health:
                buffed[key] = value

            elif isinstance(value, ValueRange):
                buffed[key] = self.buff_damage_range(key, value)

            else:
                buffed[key] = self.buff(key, value)

        return buffed

    @classmethod
    def modifier_at(cls, stat_name: str, level: int, /) -> BuffModifier:
        """Returns an object interpretable as an int or the buff's str representation
        at given level.
        """
        if STATS[stat_name].buff == "+":
            return BuffModifier(cls.HP_INCREASES[level], False)

        return BuffModifier(cls.get_percent(stat_name, level))

    def modifier_of(self, stat_name: str, /) -> BuffModifier:
        """Returns an object that can be interpreted as an int or the buff's str representation."""
        return self.modifier_at(stat_name, self.levels[stat_name])

    @classmethod
    def get_percent(cls, stat_name: str, level: int) -> int:
        """Returns an int representing the precentage for the stat's modifier."""

        literal_buff = STATS[stat_name].buff

        if literal_buff == "+%":
            return cls.BASE_PERCENT[level]

        if literal_buff == "+2%":
            return cls.BASE_PERCENT[level] * 2

        if literal_buff == "-%":
            return -cls.BASE_PERCENT[level]

        if literal_buff == "+":
            raise TypeError(f"Stat {stat_name!r} has absolute increase")

        raise ValueError(f"Stat {stat_name!r} has no buffs associated")

    @classmethod
    def iter_modifiers_of(cls, stat_name: str) -> t.Iterator[BuffModifier]:
        """Iterator over the modifiers of a stat from 0 to its maximum level."""
        for level in range(cls.max_level_of(stat_name) + 1):
            yield cls.modifier_at(stat_name, level)

    @classmethod
    def max_level_of(cls, stat_name: str) -> int:
        """Get the maximum level for a given buff."""
        if STATS[stat_name].buff == "+":
            return len(cls.HP_INCREASES) - 1

        return len(cls.BASE_PERCENT) - 1

    @classmethod
    def maxed(cls) -> Self:
        """Factory method returning `ArenaBuffs` with all levels set to max."""

        max_buffs = cls()
        levels = max_buffs.levels
        for key in levels:
            levels[key] = cls.max_level_of(key)

        setattr(cls, "maxed", staticmethod(lambda: max_buffs))

        return max_buffs


MAX_BUFFS = ArenaBuffs.maxed()


def abbreviate_names(names: t.Iterable[Name], /) -> dict[str, set[Name]]:
    """Returns dict of abbrevs: EFA => Energy Free Armor"""
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


def next_tier(current: Tier, /) -> Tier:
    """Returns the next tier in line."""
    return Tier.__call__(current.level + 1)
