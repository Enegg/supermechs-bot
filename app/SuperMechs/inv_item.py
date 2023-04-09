from __future__ import annotations

import csv
import typing as t
import uuid
from bisect import bisect_left
from pathlib import Path

from attrs import Factory, define, field
from typing_extensions import Self

from shared.decorators import cached_slot_property

from .core import AnyStats, TransformRange, next_tier
from .enums import Element, Tier, Type
from .errors import MaxPowerError, MaxTierError
from .item import Item, ItemProto, Tags
from .stat_handler import ItemStatsContainer
from .typedefs import ID, Name

__all__ = ("InvItem", "InvItemProto")


def _load_power_data_files() -> t.Iterator[dict[Tier, tuple[int, ...]]]:
    path = Path(__file__).parent / "static"
    file_names = ("default_powers.csv", "lm_item_powers.csv", "reduced_powers.csv")
    iterables = (Tier, (Tier.LEGENDARY, Tier.MYTHICAL), (Tier.LEGENDARY, Tier.MYTHICAL))

    for file_name, rarities in zip(file_names, iterables):
        file_path = path / file_name

        with file_path.open(newline="") as file:
            rows = csv.reader(file, skipinitialspace=True)

            yield {rarity: tuple(map(int, row)) for rarity, row in zip(rarities, rows)}


_default_powers: dict[Tier, tuple[int, ...]]
_premium_powers: dict[Tier, tuple[int, ...]]
_reduced_powers: dict[Tier, tuple[int, ...]]
_loaded: bool = False


# this could very well be by IDs, but names are easier to read
REDUCED_COST_ITEMS = frozenset(("Archimonde", "Armor Annihilator", "BigDaddy", "Chaos Bringer"))


def get_power_bank(item: ItemProto) -> dict[Tier, tuple[int, ...]]:
    """Returns the power per level bank for the item."""
    global _default_powers, _premium_powers, _reduced_powers, _loaded

    if not _loaded:
        _default_powers, _premium_powers, _reduced_powers = _load_power_data_files()
        _loaded = True

    if item.name in REDUCED_COST_ITEMS:
        return _reduced_powers

    if item.transform_range.min >= Tier.LEGENDARY:
        return _premium_powers

    if item.transform_range.max <= Tier.EPIC:
        # TODO: this has special case too, but currently I have no data on that
        return _default_powers

    return _default_powers


def get_power_levels_of_item(item: InvItemProto) -> tuple[int, ...]:
    return get_power_bank(item).get(item.tier, (0,))


class InvItemProto(ItemProto, t.Protocol):
    @property
    def tier(self) -> Tier:
        ...

    @cached_slot_property
    def level(self) -> int:
        ...

    @cached_slot_property
    def current_stats(self) -> AnyStats:
        ...


@define(kw_only=True)
class InvItem:
    """Represents an item inside inventory."""

    base: Item

    @property
    def id(self) -> ID:
        return self.base.id

    @property
    def pack_key(self) -> str:
        return self.base.pack_key

    @property
    def name(self) -> Name:
        return self.base.name

    @property
    def type(self) -> Type:
        return self.base.type

    @property
    def element(self) -> Element:
        return self.base.element

    @property
    def transform_range(self) -> TransformRange:
        return self.base.transform_range

    @property
    def stats(self) -> ItemStatsContainer:
        return self.base.stats

    @property
    def tags(self) -> Tags:
        return self.base.tags

    tier: Tier
    power: int = 0
    UUID: uuid.UUID = Factory(uuid.uuid4)
    _level: int = field(init=False, repr=False, eq=False)
    _current_stats: AnyStats = field(init=False, repr=False, eq=False)

    @property
    def maxed(self) -> bool:
        """Whether the item has reached the maximum power for its tier."""
        return self.power == self.max_power

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier."""
        return get_power_levels_of_item(self)[-1]

    @cached_slot_property
    def current_stats(self) -> AnyStats:
        """The stats of this item at its particular tier and level."""
        return self.base.stats[self.tier].at(self.level)

    @cached_slot_property
    def level(self) -> int:
        """The level of this item."""
        del self.current_stats
        levels = get_power_levels_of_item(self)
        return bisect_left(levels, self.power) + 1

    def __str__(self) -> str:
        level = "max" if self.maxed else self.level
        return f"[{self.tier.name[0]}] {self.name} lvl {level}"

    def add_power(self, power: int) -> None:
        """Adds power to the item."""

        if power < 0:
            raise ValueError("Power cannot be negative")

        if self.maxed:
            raise MaxPowerError(self)

        del self.level
        self.power = min(self.power + power, self.max_power)

    def ready_to_transform(self) -> bool:
        """Returns True if item has enough power to transform
        and hasn't reached max transform tier, False otherwise"""
        return self.maxed and self.tier < self.transform_range.max

    def transform(self) -> None:
        """Transforms the item to higher tier, if it has enough power"""
        if not self.maxed:
            raise ValueError("Cannot transform a non-maxed item")

        if self.tier is self.transform_range.max:
            raise MaxTierError(self)

        self.tier = next_tier(self.tier)
        self.power = 0

    @classmethod
    def from_item(cls, item: Item, /, *, maxed: bool = False) -> Self:
        return cls(base=item, tier=item.transform_range.max if maxed else item.transform_range.min)
