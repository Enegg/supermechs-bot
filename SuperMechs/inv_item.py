import csv
from dataclasses import dataclass, field
import typing as t
import uuid

from utils import Proxied, binary_find_near_index, proxy

from .enums import Element, Rarity, RarityRange
from .errors import MaxPowerReached, MaxTierReached
from .item import Item
from .types import Attachment, Attachments, AttachmentType

from PIL.Image import Image

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


@dataclass(slots=True)
@proxy("underlying")
class InvItem(t.Generic[AttachmentType]):
    """Represents item inside inventory."""

    underlying: Item[AttachmentType]

    name: t.ClassVar[Proxied[str]]
    rarity: t.ClassVar[Proxied[RarityRange]]
    element: t.ClassVar[Proxied[Element]]
    type: t.ClassVar[Proxied[str]]
    image: t.ClassVar[Proxied[Image]]

    tier: Rarity = field(hash=False)
    power: int = field(default=0, hash=False)
    UUID: uuid.UUID = field(default_factory=uuid.uuid4)
    _level: int | None = field(default=None, init=False, hash=False)
    maxed: bool = field(init=False, hash=False)

    def __post_init__(self) -> None:
        self.maxed = self.tier is Rarity.DIVINE or self.power >= self.max_power

    def __str__(self) -> str:
        return f"{self.underlying}, {self.tier}, lvl {self.level}"

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
    def from_item(cls, item: Item[AttachmentType]) -> "InvItem[AttachmentType]":
        return cls(underlying=item, tier=item.rarity.max)


AnyInvItem = InvItem[Attachment] | InvItem[Attachments] | InvItem[None]
