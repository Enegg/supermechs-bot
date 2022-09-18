import csv
import typing as t
import uuid
from bisect import bisect_left

from attrs import Factory, define, field

from .core import TransformRange
from .enums import Element, Rarity, Type
from .errors import MaxPowerReached, MaxTierReached
from .game_types import AnyStats, Attachment, Attachments, AttachmentType
from .images import AttachedImage
from .item import Item, Tags
from .utils import Proxied, proxy

__all__ = ("InvItem", "AnyInvItem", "InvItemSlot")

with (
    open("SuperMechs/static/default_powers.csv", newline="") as file1,
    open("SuperMechs/static/lm_item_powers.csv", newline="") as file2,
    open("SuperMechs/static/reduced_powers.csv", newline="") as file3,
):
    rows1 = csv.reader(file1, skipinitialspace=True)
    rows2 = csv.reader(file2, skipinitialspace=True)
    rows3 = csv.reader(file3, skipinitialspace=True)

    DEFAULT_POWERS: dict[Rarity, tuple[int, ...]] = {
        rarity: tuple(map(int, row)) for rarity, row in zip(Rarity, rows1)
    }

    LM_ITEM_POWERS: dict[Rarity, tuple[int, ...]] = {
        rarity: tuple(map(int, row)) for rarity, row in zip((Rarity.L, Rarity.M), rows2)
    }

    REDUCED_POWERS: dict[Rarity, tuple[int, ...]] = {
        rarity: tuple(map(int, row)) for rarity, row in zip((Rarity.L, Rarity.M), rows3)
    }

REDUCED_COST_ITEMS = frozenset(("Archimonde", "Armor Annihilator"))


@define(kw_only=True)
@proxy("base")
class InvItem(t.Generic[AttachmentType]):
    """Represents an item inside inventory."""

    base: Item[AttachmentType]

    id: Proxied[int] = field(init=False)
    name: Proxied[str] = field(init=False)
    type: Proxied[Type] = field(init=False)
    element: Proxied[Element] = field(init=False)
    transform_range: Proxied[TransformRange] = field(init=False)
    image: Proxied[AttachedImage[AttachmentType]] = field(init=False)
    tags: Proxied[Tags] = field(init=False)

    tier: Rarity
    power: int = 0
    UUID: uuid.UUID = Factory(uuid.uuid4)
    _level: int | None = field(default=None, init=False)
    maxed: bool = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.maxed = self.tier is Rarity.DIVINE or self.power >= self.max_power

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

        if self.power == self.max_power:
            self.maxed = True

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

        self.tier = self.transform_range.next_tier(self.tier)
        self.power = 0
        self.maxed = self.tier is not Rarity.DIVINE

    @property
    def stats(self) -> AnyStats:
        """The stats of this item at its particular tier and level."""
        return self.base.stats.at(self.tier, self.level)

    @property
    def level(self) -> int:
        """The level of this item."""

        if self._level is not None:
            return self._level

        if self.tier is Rarity.DIVINE:
            return 0

        levels = self.get_power_bank()[self.tier]
        self._level = bisect_left(levels, self.power)
        return self._level

    @level.deleter
    def level(self) -> None:
        self._level = None

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier"""

        if self.tier is Rarity.DIVINE:
            return 0

        return self.get_power_bank()[self.tier][-1]

    def get_power_bank(self) -> dict[Rarity, tuple[int, ...]]:
        """Returns the power per level bank for the item"""

        if self.name in REDUCED_COST_ITEMS:
            return REDUCED_POWERS

        if self.transform_range.min >= Rarity.LEGENDARY:
            return LM_ITEM_POWERS

        if self.transform_range.max <= Rarity.EPIC:
            # TODO: this has special case too, but currently I have no data on that
            return DEFAULT_POWERS

        return DEFAULT_POWERS

    def has_any_of_stats(self, *stats: str) -> bool:
        """Check if any of the stat keys appear in the item's stats."""
        return not self.stats.keys().isdisjoint(stats)

    @classmethod
    def from_item(
        cls, item: Item[AttachmentType], /, *, maxed: bool = False
    ) -> "InvItem[AttachmentType]":
        return cls(base=item, tier=item.transform_range.max if maxed else item.transform_range.min)


AnyInvItem = InvItem[Attachment] | InvItem[Attachments] | InvItem[None]
InvItemSlot = InvItem[AttachmentType] | None
