from __future__ import annotations

import csv
import uuid
from bisect import bisect_left
from pathlib import Path

from attrs import Factory, define, field
from typing_extensions import Self

from shared.decorators import cached_slot_property

from .core import AnyStats, TransformRange, next_tier
from .enums import Element, Tier, Type
from .errors import MaxPowerReached, MaxTierReached
from .item import Item, ItemProto, Tags
from .stat_handler import ItemStatsContainer
from .typedefs import ID, Name

__all__ = ("InvItem",)


def _load_power_data_files():
    path = Path(__file__).parent / "static"
    file_names = ("default_powers.csv", "lm_item_powers.csv", "reduced_powers.csv")
    iterables = (Tier, (Tier.LEGENDARY, Tier.MYTHICAL), (Tier.LEGENDARY, Tier.MYTHICAL))

    for file_name, rarities in zip(file_names, iterables):
        file_path = path / file_name

        with file_path.open(newline="") as file:
            rows = csv.reader(file, skipinitialspace=True)

            yield {rarity: tuple(map(int, row)) for rarity, row in zip(rarities, rows)}


DEFAULT_POWERS, LM_ITEM_POWERS, REDUCED_POWERS = _load_power_data_files()
REDUCED_COST_ITEMS = frozenset(("Archimonde", "Armor Annihilator", "BigDaddy", "Chaos Bringer"))


def get_power_bank(item: ItemProto) -> dict[Tier, tuple[int, ...]]:
    """Returns the power per level bank for the item."""

    if item.name in REDUCED_COST_ITEMS:
        return REDUCED_POWERS

    if item.transform_range.min >= Tier.LEGENDARY:
        return LM_ITEM_POWERS

    if item.transform_range.max <= Tier.EPIC:
        # TODO: this has special case too, but currently I have no data on that
        return DEFAULT_POWERS

    return DEFAULT_POWERS


def get_power_levels_of_item(item: InvItem) -> tuple[int, ...]:
    powers = get_power_bank(item)
    return powers.get(item.tier, (0,))


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

    def __str__(self) -> str:
        level = "max" if self.maxed else self.level
        return f"{self.name} at {self.tier.name.lower()} lvl {level}"

    def add_power(self, power: int) -> None:
        """Adds power to the item."""

        if power < 0:
            raise ValueError("Power cannot be negative")

        if self.maxed:
            raise MaxPowerReached(self)

        del self.level
        self.power = min(self.power + power, self.max_power)

    def can_transform(self) -> bool:
        """Returns True if item has enough power to transform
        and hasn't reached max transform tier, False otherwise"""
        return self.maxed and self.tier < self.transform_range.max

    def transform(self) -> None:
        """Transforms the item to higher tier, if it has enough power"""
        if not self.maxed:
            raise ValueError("Cannot transform a non-maxed item")

        if self.tier is self.transform_range.max:
            raise MaxTierReached(self)

        self.tier = next_tier(self.tier)
        self.power = 0

    @cached_slot_property
    def current_stats(self) -> AnyStats:
        """The stats of this item at its particular tier and level."""
        return self.base.stats[self.tier].at(self.level)

    @cached_slot_property
    def level(self) -> int:
        """The level of this item."""
        del self.current_stats
        levels = get_power_levels_of_item(self)
        return bisect_left(levels, self.power)

    @property
    def maxed(self) -> bool:
        """Whether the item has reached the maximum power for its tier."""
        return self.power == self.max_power

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier."""
        return get_power_levels_of_item(self)[-1]

    @classmethod
    def from_item(cls, item: Item, /, *, maxed: bool = False) -> Self:
        return cls(base=item, tier=item.transform_range.max if maxed else item.transform_range.min)
