from typing import Literal, Self

import attrs

from discord.urls import CDN

__all__ = ("Asset",)


@attrs.frozen
class Asset:
    type Size = Literal[0, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    type Format = Literal["png", "webp", "gif"]

    base_url: str
    """The base URL of the asset, excluding format and size."""
    format: Format = "png"
    """The file format of the asset."""
    size: Size = 0
    """The dimensions of the image asset. `0` uses the default size for that asset."""

    def with_format(self, format: Format, /) -> Self:
        # TODO: copy.replace
        return attrs.evolve(self, format=format)

    def with_size(self, size: Size, /) -> Self:
        return attrs.evolve(self, size=size)

    @property
    def full_url(self) -> str:
        """The full URL of the asset, including format and size."""
        if self.size == 0:
            return f"{self.base_url}.{self.format}"
        return f"{self.base_url}.{self.format}?size={self.size}"

    @classmethod
    def from_emoji(cls, emoji_id: int, animated: bool = False) -> Self:
        return cls(base_url=f"{CDN}/emojis/{emoji_id}", format="gif" if animated else "webp")
