from __future__ import annotations

import typing as t
import uuid

from utils import MISSING

from .enums import Rarity
from .item import Item
from .types import Attachment, Attachments, AttachmentType


class InvItem(Item[AttachmentType]):
    """Represents item inside inventory."""

    def __init__(
        self,
        underlying: Item[AttachmentType],
        tier: Rarity,
        power: int = 0,
        UUID: uuid.UUID = MISSING
    ) -> None:
        self.underlying = underlying
        self.tier = tier
        self.power = power

        if isinstance(UUID, uuid.UUID):
            self.UUID = UUID

        elif UUID is MISSING:
            self.UUID = uuid.uuid4()

        else:
            raise TypeError("Invalid type for UUID passed")

    def __getattr__(self, name: t.Any):
        try:
            return getattr(self.underlying, name)

        except AttributeError:
            raise AttributeError(f'{type(self).__name__} object has no attribute "{name}"') from None

    def __repr__(self) -> str:
        return ("<InvItem item={0.underlying!r} tier={0.max_rarity}"
                " power={0.power} UUID={0.UUID}>").format(self)

    def __hash__(self) -> int:
        return hash((self.UUID, self.underlying))

    def can_transform(self) -> bool:
        """Returns True if item has enough power to transform
        and hasn't reached max transform tier, False otherwise"""
        if 1 + 1 == 2:  # TODO: condition(s) for power
            return False

        if self.tier < self.max_rarity:
            return True

        return False

    def transform(self) -> None:
        """Transforms the item to higher tier, if it has enough power"""
        if not self.can_transform():
            raise ValueError("Not enough power to transform")

        self.tier = self.rarity.next_tier(self.tier)
        self.power = 0

    @property
    def min_rarity(self) -> Rarity:
        return self.underlying.rarity.min

    @property
    def max_rarity(self) -> Rarity:
        return self.underlying.rarity.max

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier"""
        upper = self.max_rarity
        lower = self.min_rarity
        current = self.tier
        item = self.underlying

        return 0

    @classmethod
    def from_item(cls, item: Item[AttachmentType]) -> InvItem[AttachmentType]:
        return cls(underlying=item, tier=item.rarity.max)


AnyInvItem = InvItem[Attachment] | InvItem[Attachments] | InvItem[None]
