import math
from collections import abc
from enum import Enum
from typing import Any, NamedTuple, SupportsFloat

from smparse.converter import converter
from smparse.packs.models import AnyItemPack, ItemPackV1, ItemPackV2, ItemPackV3

from supermechs.item import ItemStats


class Sentinel(Enum):
    instance = None


class _NameAndAddon(NamedTuple):
    name: str
    has_addon: bool = False


_STAT_NAME_TABLE: abc.Mapping[str, _NameAndAddon] = {
    "weight": _NameAndAddon("weight"),
    "health": _NameAndAddon("hit_points"),
    "eneCap": _NameAndAddon("energy_capacity"),
    "eneReg": _NameAndAddon("regeneration"),
    "heaCap": _NameAndAddon("heat_capacity"),
    "heaCol": _NameAndAddon("cooling"),
    "phyRes": _NameAndAddon("physical_resistance"),
    "expRes": _NameAndAddon("explosive_resistance"),
    "eleRes": _NameAndAddon("electric_resistance"),
    "bulletsCap": _NameAndAddon("bullets_capacity"),
    "rocketsCap": _NameAndAddon("rockets_capacity"),
    "walk": _NameAndAddon("walk"),
    "jump": _NameAndAddon("jump"),
    "phyDmg": _NameAndAddon("physical_damage", True),
    "phyResDmg": _NameAndAddon("physical_resistance_damage"),
    "eleDmg": _NameAndAddon("electric_damage", True),
    "eneDmg": _NameAndAddon("energy_damage"),
    "eneCapDmg": _NameAndAddon("energy_capacity_damage"),
    "eneRegDmg": _NameAndAddon("regeneration_damage"),
    "eleResDmg": _NameAndAddon("electric_resistance_damage"),
    "expDmg": _NameAndAddon("explosive_damage", True),
    "heaDmg": _NameAndAddon("heat_damage"),
    "heaCapDmg": _NameAndAddon("heat_capacity_damage"),
    "heaColDmg": _NameAndAddon("cooling_damage"),
    "expResDmg": _NameAndAddon("explosive_resistance_damage"),
    "range": _NameAndAddon("range", True),
    "push": _NameAndAddon("push"),
    "pull": _NameAndAddon("pull"),
    "recoil": _NameAndAddon("recoil"),
    "advance": _NameAndAddon("advance"),
    "retreat": _NameAndAddon("retreat"),
    "uses": _NameAndAddon("uses"),
    "backfire": _NameAndAddon("backfire"),
    "heaCost": _NameAndAddon("heat_generation"),
    "eneCost": _NameAndAddon("energy_cost"),
    "bulletsCost": _NameAndAddon("bullets_cost"),
    "rocketsCost": _NameAndAddon("rockets_cost"),
}


def none_to_nan(value: SupportsFloat | None, /) -> float:
    return math.nan if value is None else float(value)


@converter.register_structure_hook
def structure_stats(obj: abc.Mapping[str, Any | None | list[Any | None]], _: type) -> ItemStats:
    stats_mapping: dict[str, float] = {}
    problems: list[Exception] = []

    for key, (name, has_addon) in _STAT_NAME_TABLE.items():
        try:
            match obj.get(key, Sentinel.instance):
                case Sentinel.instance:
                    continue

                case [value]:
                    stats_mapping[name] = none_to_nan(value)

                case [value, addon] if has_addon:
                    stats_mapping[name] = none_to_nan(value)
                    stats_mapping[f"{name}_addon"] = none_to_nan(addon)

                case [*values]:
                    how_many = "2 values" if has_addon else "1 value"
                    msg = f"At {key}: expected at most {how_many}, got {len(values)}"
                    problems.append(ValueError(msg))

                case value:
                    stats_mapping[name] = none_to_nan(value)

        # float conversion
        except (TypeError, ValueError) as err:
            problems.append(err)

    if problems:
        msg = "Problems while structuring stats:"
        raise ExceptionGroup(msg, problems) from None

    return ItemStats(**stats_mapping)


def structure_raw(data: abc.Mapping[str, Any], /) -> AnyItemPack:
    match data.get("version", Sentinel.instance):
        case 1 | "1" | Sentinel.instance:
            format = ItemPackV1

        case 2 | "2":
            format = ItemPackV2

        case 3 | "3":
            format = ItemPackV3

        case str() as ver if not ver.isdecimal():
            msg = f"Version should be numeric, got {ver!r:.10}"
            raise ValueError(msg) from None

        case str() | int() as ver:
            msg = f'Unknown version: "{ver}"'
            raise NotImplementedError(msg) from None

        case invalid:
            msg = f'"version" is a {type(invalid).__name__}, expected an int or str'
            raise TypeError(msg) from None

    return converter.structure(data, format)
