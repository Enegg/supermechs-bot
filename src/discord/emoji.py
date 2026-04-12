import datetime as dt
from typing import Literal, override

import msgspec

import disnake
from discord.asset import Asset
from disnake import PartialEmoji
from disnake.utils import snowflake_time

__all__ = ("AnyEmoji", "CustomEmoji", "UnicodeEmoji")

type AnyEmoji = UnicodeEmoji | CustomEmoji


class UnicodeEmoji(msgspec.Struct):
    name: str

    @property
    def id(self) -> None:
        return None

    @property
    def animated(self) -> Literal[False]:
        return False

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


class CustomEmoji(msgspec.Struct):
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

    def to_asset(self) -> Asset.StaticOrGifAsset:
        return Asset.from_emoji(self.id, self.animated)
