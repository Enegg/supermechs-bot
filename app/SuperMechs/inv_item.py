import csv
import typing as t
import uuid
from bisect import bisect_left
from pathlib import Path

from attrs import Factory, define, field

from shared.utils import cached_slot_property, proxied
from typeshed import ID, Name

from .core import TransformRange
from .enums import Element, Tier, Type
from .errors import MaxPowerReached, MaxTierReached
from .images import AttachedImage, Attachment, Attachments, AttachmentType
from .item import Item, Tags
from .typedefs.game_types import AnyStats

__all__ = ("InvItem", "AnyInvItem", "SlotType")


def _load_power_data_files():
    path = Path(__file__).parent / "static"
    file_names = ("default_powers.csv", "lm_item_powers.csv", "reduced_powers.csv")
    iterables = (Tier, (Tier.L, Tier.M), (Tier.L, Tier.M))

    for file_name, rarities in zip(file_names, iterables):
        file_path = path / file_name

        with file_path.open(newline="") as file:
            rows = csv.reader(file, skipinitialspace=True)

            yield {rarity: tuple(map(int, row)) for rarity, row in zip(rarities, rows)}


DEFAULT_POWERS, LM_ITEM_POWERS, REDUCED_POWERS = _load_power_data_files()
REDUCED_COST_ITEMS = frozenset(("Archimonde", "Armor Annihilator"))


@define(kw_only=True)
class InvItem(t.Generic[AttachmentType]):
    """Represents an item inside inventory."""

    base: Item[AttachmentType]

    id = proxied[ID]("base")
    name = proxied[Name]("base")
    type = proxied[Type]("base")
    element = proxied[Element]("base")
    transform_range = proxied[TransformRange]("base")
    image = proxied[AttachedImage[AttachmentType]]("base")
    tags = proxied[Tags]("base")

    tier: Tier
    power: int = 0
    UUID: uuid.UUID = Factory(uuid.uuid4)
    maxed: bool = field(init=False)
    _level: int = field(init=False, repr=False, eq=False)

    def __attrs_post_init__(self) -> None:
        self.maxed = self.tier is Tier.DIVINE or self.power >= self.max_power

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
        self.maxed = self.tier is not Tier.DIVINE

    @property
    def stats(self) -> AnyStats:
        """The stats of this item at its particular tier and level."""
        return self.base.stats.at(self.tier, self.level)

    @cached_slot_property
    def level(self) -> int:
        """The level of this item."""
        if self.tier is Tier.DIVINE:
            return 0

        levels = self.get_power_bank()[self.tier]
        return bisect_left(levels, self.power)

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier"""

        if self.tier is Tier.DIVINE:
            return 0

        return self.get_power_bank()[self.tier][-1]

    def get_power_bank(self) -> dict[Tier, tuple[int, ...]]:
        """Returns the power per level bank for the item"""

        if self.name in REDUCED_COST_ITEMS:
            return REDUCED_POWERS

        if self.transform_range.min >= Tier.LEGENDARY:
            return LM_ITEM_POWERS

        if self.transform_range.max <= Tier.EPIC:
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
SlotType = InvItem[AttachmentType] | None
