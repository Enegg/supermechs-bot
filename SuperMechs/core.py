from __future__ import annotations

import typing as t

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


class Stat(t.NamedTuple):
    name: str
    emoji: str


# fmt: off
STAT_NAMES = dict(
    weight   =Stat("Weight",                "<:weight:725870760484143174>"),
    health   =Stat("HP",                    "<:health:725870887588462652>"),
    eneCap   =Stat("Energy",                "<:energy:725870941883859054>"),
    eneReg   =Stat("Regeneration",           "<:regen:725871003665825822>"),
    heaCap   =Stat("Heat",                    "<:heat:725871043767435336>"),
    heaCol   =Stat("Cooling",              "<:cooling:725871075778363422>"),
    phyRes   =Stat("Physical resistance",   "<:phyres:725871121051811931>"),
    expRes   =Stat("Explosive resistance",  "<:expres:725871136935772294>"),
    eleRes   =Stat("Electric resistance",  "<:elecres:725871146716758077>"),
    phyDmg   =Stat("Physical damage",       "<:phydmg:725871208830074929>"),
    phyResDmg=Stat("Resistance drain",   "<:phyresdmg:725871259635679263>"),
    expDmg   =Stat("Explosive damage",      "<:expdmg:725871223338172448>"),
    heaDmg   =Stat("Heat damage",           "<:headmg:725871613639393290>"),
    heaCapDmg=Stat("Max heat damage",   "<:heatcapdmg:725871478083551272>"),
    heaColDmg=Stat("Cooling damage",    "<:coolingdmg:725871499281563728>"),
    expResDmg=Stat("Resistance drain",   "<:expresdmg:725871281311842314>"),
    eleDmg   =Stat("Electric damage",       "<:eledmg:725871233614479443>"),
    eneDmg   =Stat("Energy damage",         "<:enedmg:725871599517171719>"),
    eneCapDmg=Stat("Max energy damage",  "<:enecapdmg:725871420126789642>"),
    eneRegDmg=Stat("Regeneration damage", "<:regendmg:725871443815956510>"),
    eleResDmg=Stat("Resistance drain",   "<:eleresdmg:725871296381976629>"),
    range    =Stat("Range",                  "<:range:725871752072134736>"),
    push     =Stat("Knockback",               "<:push:725871716613488843>"),
    pull     =Stat("Pull",                    "<:pull:725871734141616219>"),
    recoil   =Stat("Recoil",                "<:recoil:725871778282340384>"),
    retreat  =Stat("Retreat",              "<:retreat:725871804236955668>"),
    advance  =Stat("Advance",              "<:advance:725871818115907715>"),
    walk     =Stat("Walking",                 "<:walk:725871844581834774>"),
    jump     =Stat("Jumping",                 "<:jump:725871869793796116>"),
    uses     =Stat("Uses",                    "<:uses:725871917923303688>"),
    backfire =Stat("Backfire",            "<:backfire:725871901062201404>"),
    heaCost  =Stat("Heat cost",            "<:heatgen:725871674007879740>"),
    eneCost  =Stat("Energy cost",         "<:eneusage:725871660237979759>"))
# fmt: on


class GameVars(t.NamedTuple):
    MAX_WEIGHT: int = 1000
    OVERWEIGHT: int = 10
    PENALTIES: dict[str, int] = {"health": 15}

    @property
    def MAX_OVERWEIGHT(self) -> int:
        return self.MAX_WEIGHT + self.OVERWEIGHT


DEFAULT_VARS = GameVars()


class ArenaBuffs:
    ref_def = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20)
    ref_hp = (0, +10, +30, +60, 90, 120, 150, 180, +220, +260, 300, 350)
    stat_ref = (
        "eneCap",
        "eneReg",
        "eneDmg",
        "heaCap",
        "heaCol",
        "heaDmg",
        "phyDmg",
        "expDmg",
        "eleDmg",
        "phyRes",
        "expRes",
        "eleRes",
        "health",
        "backfire",
    )

    def __init__(self, levels: dict[str, int] | None = None) -> None:
        self.levels = levels or dict.fromkeys(self.stat_ref, 0)

    def __getitem__(self, key: str) -> int:
        return self.levels[key]

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} "
            + ", ".join(f"{stat}={lvl}" for stat, lvl in self.levels.items())
            + ">"
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
        if stat == "health":
            return f"+{cls.ref_hp[level]}"

        return f"{cls.get_percent(stat, level):+}%"

    def buff_as_str_aware(self, stat: str) -> str:
        return self.buff_as_str(stat, self.levels[stat])

    @classmethod
    def iter_as_str(cls, stat: str) -> t.Iterator[str]:
        levels = len(cls.ref_hp) if stat == "health" else len(cls.ref_def)

        for n in range(levels):
            yield cls.buff_as_str(stat, n)

    @classmethod
    def maxed(cls) -> ArenaBuffs:
        self = cls.__new__(cls)

        self.levels = dict.fromkeys(cls.stat_ref, len(cls.ref_def) - 1)
        self.levels["health"] = len(cls.ref_hp) - 1

        return self


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
