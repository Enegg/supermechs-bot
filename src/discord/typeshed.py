from collections import abc
from typing import Literal

import disnake

__all__ = ("AutocompleteReturnType", "EmbedColorType", "EmojiType")

type AutocompleteReturnType = (
    abc.Sequence[str | disnake.Localized[str]] | abc.Mapping[str, str | disnake.Localized[str]]
)
type EmbedColorType = disnake.Color | int | None
type EmojiType = str | disnake.Emoji | disnake.PartialEmoji

type AssetSize = Literal[16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
type AssetFormat = Literal["png", "webp", "gif"]
