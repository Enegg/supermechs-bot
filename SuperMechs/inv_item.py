from __future__ import annotations

import csv
import typing as t
import uuid

from utils import ProxyType, binary_find_near_index

from .enums import Rarity
from .errors import MaxPowerReached, MaxTierReached
from .item import Item
from .types import Attachment, Attachments, AttachmentType

with (
    open("SuperMechs/GameData/default_powers.csv", newline="") as file1,
    open("SuperMechs/GameData/lm_item_powers.csv", newline="") as file2,
    open("SuperMechs/GameData/reduced_powers.csv", newline="") as file3,
):
    rows1 = csv.reader(file1, skipinitialspace=True)
    rows2 = csv.reader(file2, skipinitialspace=True)
    rows3 = csv.reader(file3, skipinitialspace=True)

    DEFAULT_POWERS: dict[Rarity, tuple[int, ...]] = {
        rarity: tuple(map(int, row)) for rarity, row in zip(Rarity, rows1)
    }

    LM_POWERS: dict[Rarity, tuple[int, ...]] = {
        rarity: tuple(map(int, row)) for rarity, row in zip((Rarity.L, Rarity.M), rows2)
    }

    REDUCED_POWERS: dict[Rarity, tuple[int, ...]] = {
        rarity: tuple(map(int, row)) for rarity, row in zip((Rarity.L, Rarity.M), rows3)
    }

REDUCED_COST_ITEMS = {"Archimonde", "Armor Annihilator"}


class InvItem(Item[AttachmentType], metaclass=ProxyType, var="underlying"):
    """Represents item inside inventory."""

    def __init__(
        self,
        underlying: Item[AttachmentType],
        tier: Rarity,
        power: int = 0,
        UUID: uuid.UUID | None = None,
    ) -> None:
        self.underlying = underlying
        self.tier = tier
        self.power = power
        self.maxed = tier is Rarity.DIVINE or power >= self.max_power
        self._level: int | None = None

        if isinstance(UUID, uuid.UUID):
            self.UUID = UUID

        elif UUID is None:
            self.UUID = uuid.uuid4()

        else:
            raise TypeError("Invalid type for UUID passed")

    def __repr__(self) -> str:
        return (
            f"<InvItem item={self.underlying!r} tier={self.tier}"
            f" power={self.power} UUID={self.UUID} at 0x{id(self):016X}>"
        )

    def __hash__(self) -> int:
        # we don't take into account level, power etc. as there shouldn't ever be
        # two items with same UUID
        # technically could exclude the underlying item too
        return hash((self.UUID, self.underlying))

    def add_power(self, power: int) -> None:
        """Adds power to the item"""

        if self.maxed:
            raise MaxPowerReached(self)

        if power < 0:
            raise ValueError("Power cannot be negative")

        if (result := self.power + power) >= self.max_power:
            result = self.max_power
            self.maxed = True

        del self.level
        self.power = result

    def can_transform(self) -> bool:
        """Returns True if item has enough power to transform
        and hasn't reached max transform tier, False otherwise"""
        if not self.maxed:
            return False

        return self.tier < self.rarity.max

    def transform(self) -> None:
        """Transforms the item to higher tier, if it has enough power"""
        if not self.maxed:
            raise ValueError("Not enough power to transform")

        if self.tier is self.rarity.max:
            raise MaxTierReached(self)

        self.tier = self.rarity.next_tier(self.tier)
        self.power = 0
        self.maxed = self.tier is not Rarity.DIVINE

    @property
    def level(self) -> int:
        """The level the item is currently at"""

        if self._level is not None:
            return self._level

        levels = self.get_bank()[self.tier]
        self._level = binary_find_near_index(levels, self.power, 0, len(levels))
        return self._level

    @level.deleter
    def level(self) -> None:
        self._level = None

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier"""

        if self.tier is Rarity.DIVINE:
            return 0

        return self.get_bank()[self.tier][-1]

    def get_bank(self) -> dict[Rarity, tuple[int, ...]]:
        """Returns the power per level bank for the item"""

        if self.name in REDUCED_COST_ITEMS:
            return REDUCED_POWERS

        if self.rarity.min >= Rarity.LEGENDARY:
            return LM_POWERS

        if self.rarity.max <= Rarity.EPIC:
            # TODO: this has special case too, but currently I have no data on that
            return DEFAULT_POWERS

        return DEFAULT_POWERS

    @classmethod
    def from_item(cls, item: Item[AttachmentType]) -> InvItem[AttachmentType]:
        return cls(underlying=item, tier=item.rarity.max)


AnyInvItem = InvItem[Attachment] | InvItem[Attachments] | InvItem[None]
