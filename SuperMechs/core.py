from __future__ import annotations

import typing as t
from json import load

from typing_extensions import Self

from utils import MISSING

from .types import AnyStatKey, AnyStats, StatDict

WORKSHOP_STATS: t.Final = (
    "weight",
    "health",
    "eneCap",
    "eneReg",
    "heaCap",
    "heaCol",
    "phyRes",
    "expRes",
    "eleRes",
    "bulletCap",
    "rocketCap",
    "walk",
    "jump",
)


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
    name: Name
    emoji: str = "❔"
    beneficial: bool = True
    buff: tuple[str, int] | None = None

    @classmethod
    def from_dict(cls, json: StatDict) -> Self:
        buff = json.get("buff", None)
        new = {
            "name": Name(**json["names"]),
            "beneficial": "beneficial" not in json,
            "buff": None if buff is None else (buff["mode"], buff["range"]),
        }
        if emoji := json.get("emoji"):
            new["emoji"] = emoji

        return cls(**new)


with open("SuperMechs/GameData/StatData.json") as file:
    json: dict[AnyStatKey, StatDict] = load(file)

    STATS = {stat_key: Stat.from_dict(value) for stat_key, value in json.items()}


class GameVars(t.NamedTuple):
    MAX_WEIGHT: int = 1000
    OVERWEIGHT: int = 10
    PENALTIES: dict[str, int] = {"health": 15}

    @property
    def MAX_OVERWEIGHT(self) -> int:
        return self.MAX_WEIGHT + self.OVERWEIGHT


DEFAULT_VARS = GameVars()


class ArenaBuffs:
    # fmt: off
    ref_def = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20)
    ref_hp = (0, +10, +30, +60, 90, 120, 150, 180, +220, +260, 300, 350)
    stat_ref = (
        "eneCap", "eneReg", "eneDmg", "heaCap", "heaCol", "heaDmg", "phyDmg",
        "expDmg", "eleDmg", "phyRes", "expRes", "eleRes", "health", "backfire"
    )
    # fmt: on

    def __init__(self, levels: dict[str, int] | None = None) -> None:
        self.levels = levels or dict.fromkeys(self.stat_ref, 0)

    def __getitem__(self, key: str) -> int:
        return self.levels[key]

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} "
            + ", ".join(f"{stat}={lvl}" for stat, lvl in self.levels.items())
            + f" at 0x{id(self):016X}>"
        )

    @property
    def is_at_zero(self) -> bool:
        """Whether all buffs are at level 0"""
        return all(v == 0 for v in self.levels.values())

    def total_buff(self, stat: str, value: int) -> int:
        """Buffs a value according to given stat."""
        if stat not in self.levels:
            return value

        level = self.levels[stat]

        if stat == "health":
            return value + self.ref_hp[level]

        return round(value * (1 + self.get_percent(stat, level) / 100))

    def total_buff_difference(self, stat: str, value: int) -> tuple[int, int]:
        """Buffs a value and returns the total as well as
        the difference between the total and initial value."""
        buffed = self.total_buff(stat, value)
        return buffed, buffed - value

    @classmethod
    def get_percent(cls, stat: str, level: int) -> int:
        """Returns an int representing the precentage for the stat's increase."""
        match stat:
            case "health":
                raise TypeError('"Health" stat has absolute increase, not percent')

            case "backfire":
                return -cls.ref_def[level]

            case "expRes" | "eleRes" | "phyRes":
                return cls.ref_def[level] * 2

            case _:
                return cls.ref_def[level]

    @classmethod
    def buff_as_str(cls, stat: str, level: int) -> str:
        """Returns a formatted string representation of the stat's value at the given level."""
        if stat == "health":
            return f"+{cls.ref_hp[level]}"

        return f"{cls.get_percent(stat, level):+}%"

    def buff_as_str_aware(self, stat: str) -> str:
        """Returns a formatted string representation of the stat's value."""
        return self.buff_as_str(stat, self.levels[stat])

    @classmethod
    def iter_as_str(cls, stat: str) -> t.Iterator[str]:
        levels = len(cls.ref_hp) if stat == "health" else len(cls.ref_def)

        for n in range(levels):
            yield cls.buff_as_str(stat, n)

    @classmethod
    def maxed(cls) -> ArenaBuffs:
        """Create an ArenaBuffs object with all levels maxed."""
        self = cls.__new__(cls)

        self.levels = dict.fromkeys(cls.stat_ref, len(cls.ref_def) - 1)
        self.levels["health"] = len(cls.ref_hp) - 1

        return self

    def buff_stats(self, stats: AnyStats, /, *, buff_health: bool = False) -> AnyStats:
        """Returns the buffed stats."""
        buffed: AnyStats = {}

        for key, value in stats.items():
            if key == "health" and not buff_health:
                buffed[key] = t.cast(int, value)

            elif isinstance(value, list):
                buffed[key] = [self.total_buff(key, v) for v in value]

            else:
                value = self.total_buff(key, t.cast(int, value))
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
