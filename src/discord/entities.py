import datetime as dt
from typing import Literal, Self, final, override

import msgspec

import disnake
from discord.urls import CDN
from disnake import PartialEmoji
from disnake.utils import snowflake_time

__all__ = ("AnyEmoji", "Asset", "CustomEmoji", "NullUser", "UnicodeEmoji")


@final
class NullUser(disnake.abc.User):
    __slots__ = ()

    id: int = 0
    name: str = "Unknown"
    discriminator: str = "0"
    global_name: str | None = None
    bot: bool = False

    @property
    @override
    def display_name(self) -> str:
        return self.name

    @property
    @override
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    @override
    def avatar(self) -> disnake.Asset | None:
        return None


class Asset(msgspec.Struct, frozen=True):
    """A discord asset."""

    type Size = Literal[0, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    type Format = Literal["png", "webp", "gif"]

    base_url: str
    """The base URL of the asset, excluding format and size."""
    format: Format = "png"
    """The file format of the asset."""
    size: Size = 0
    """The dimensions of the image asset. `0` uses the default size for that asset."""

    @property
    def full_url(self) -> str:
        """The full URL of the asset, including format and size."""
        if self.size == 0:
            return f"{self.base_url}.{self.format}"
        return f"{self.base_url}.{self.format}?size={self.size}"

    @classmethod
    def from_emoji(cls, emoji_id: int, animated: bool = False) -> Self:
        return cls(base_url=f"{CDN}/emojis/{emoji_id}", format="gif" if animated else "webp")


type AnyEmoji = UnicodeEmoji | CustomEmoji


@final
class UnicodeEmoji(msgspec.Struct, frozen=True):
    """Built-in unicode emoji."""

    name: str

    @property
    def id(self) -> None:
        return None

    @property
    def animated(self) -> Literal[False]:
        return False

    @override
    def __eq__(self, rhs: object, /) -> bool:
        if isinstance(rhs, __class__):
            return self.name == rhs.name

        if isinstance(rhs, str):
            return self.name == rhs

        return NotImplemented

    @override
    def __hash__(self) -> int:
        return hash(self.name)

    @override
    def __str__(self) -> str:
        return self.name

    @property
    def mention(self) -> str:
        return self.name

    def to_partial(self) -> PartialEmoji:
        return PartialEmoji(id=None, name=self.name)

    # TODO: consider grabbing those from some CDN
    def to_asset(self) -> None:
        return None


@final
class CustomEmoji(msgspec.Struct, frozen=True):
    """Application-owned emoji."""

    id: int
    name: str
    animated: bool = False

    @override
    def __eq__(self, rhs: object, /) -> bool:
        if not isinstance(rhs, __class__):
            return NotImplemented

        return self.id == rhs.id

    @override
    def __hash__(self) -> int:
        return self.id >> 4

    @override
    def __str__(self) -> str:
        return self.mention

    @property
    def created_at(self: disnake.abc.Snowflake) -> dt.datetime:
        return snowflake_time(self.id)

    @property
    def mention(self) -> str:
        if self.animated:
            return f"<a:{self.name}:{self.id}>"
        return f"<:{self.name}:{self.id}>"

    def to_partial(self) -> PartialEmoji:
        return PartialEmoji(id=self.id, name=self.name, animated=self.animated)

    def to_asset(self) -> Asset:
        return Asset.from_emoji(self.id, self.animated)
