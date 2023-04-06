from __future__ import annotations

import typing as t

from attrs import define
from typing_extensions import Self

from ..core import TransformRange
from ..enums import Tier, Type
from ..utils import MISSING
from .attachments import AnyAttachment, create_synthetic_attachment, is_attachable

if t.TYPE_CHECKING:
    from PIL.Image import Image


@define
class ItemSprite:
    image: Image = MISSING
    attachment: AnyAttachment = None

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    def _create_attachment(self, type: Type) -> None:
        if self.attachment is None and is_attachable(type):
            self.attachment = create_synthetic_attachment(*self.image.size, type)


@define
class TieredSprite:
    """Container class for the sprites of an item at its transformation tiers."""

    sprites: list[ItemSprite]
    transform_range: TransformRange

    def __getitem__(self, tier: Tier) -> ItemSprite:
        if tier not in self.transform_range:
            raise ValueError("Invalid tier")

        return self.sprites[tier.level - self.transform_range.min.level]

    @property
    def max_tier(self) -> ItemSprite:
        return self.sprites[-1]

    @classmethod
    def create_duplicated(cls, sprite: ItemSprite, transform_range: TransformRange) -> Self:
        """Duplicate the passed sprite as a sprite for every tier."""
        return cls([sprite] * len(transform_range), transform_range)
