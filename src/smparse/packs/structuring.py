import math
from collections import abc
from enum import Enum
from typing import Any, SupportsFloat, SupportsIndex

from smparse.converter import converter
from smparse.packs.models import AnyItemPack, ItemPackV1, ItemPackV2, ItemPackV3

from supermechs.item import ItemStats


class Sentinel(Enum):
    instance = None


_STAT_RENAME_TABLE: abc.Mapping[str, str] = {
    "weight": "weight",
    "health": "hit_points",
    "eneCap": "energy_capacity",
    "eneReg": "regeneration",
    "heaCap": "heat_capacity",
    "heaCol": "cooling",
    "phyRes": "physical_resistance",
    "expRes": "explosive_resistance",
    "eleRes": "electric_resistance",
    "bulletsCap": "bullets_capacity",
    "rocketsCap": "rockets_capacity",
    "walk": "walk",
    "jump": "jump",
    "phyDmg": "physical_damage",
    "phyResDmg": "physical_resistance_damage",
    "eleDmg": "electric_damage",
    "eneDmg": "energy_damage",
    "eneCapDmg": "energy_capacity_damage",
    "eneRegDmg": "regeneration_damage",
    "eleResDmg": "electric_resistance_damage",
    "expDmg": "explosive_damage",
    "heaDmg": "heat_damage",
    "heaCapDmg": "heat_capacity_damage",
    "heaColDmg": "cooling_damage",
    "expResDmg": "explosive_resistance_damage",
    "range": "range",
    "push": "push",
    "pull": "pull",
    "recoil": "recoil",
    "advance": "advance",
    "retreat": "retreat",
    "uses": "uses",
    "backfire": "backfire",
    "heaCost": "heat_generation",
    "eneCost": "energy_cost",
    "bulletsCost": "bullets_cost",
    "rocketsCost": "rockets_cost",
}
_STAT_WITH_ADDON: abc.Set[str] = {"phyDmg", "eleDmg", "expDmg", "range"}


type ConvertibleToFloat = str | SupportsFloat | SupportsIndex


def none_to_nan(value: ConvertibleToFloat | None, /) -> float:
    return math.nan if value is None else float(value)


@converter.register_structure_hook
def structure_stats(obj: abc.Mapping[str, Any | None | list[Any | None]], _: type) -> ItemStats:
    stats_mapping: dict[str, float] = {}
    problems: list[Exception] = []

    for key, name in _STAT_RENAME_TABLE.items():
        has_addon = key in _STAT_WITH_ADDON
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
        except (TypeError, ValueError, OverflowError) as err:
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
