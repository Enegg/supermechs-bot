from collections import abc

import disnake

__all__ = ("AutocompleteReturnType", "EmbedColorType", "EmojiType")

type AutocompleteReturnType = (
    abc.Sequence[str | disnake.Localized[str]] | abc.Mapping[str, str | disnake.Localized[str]]
)
type EmbedColorType = disnake.Color | int | None
type EmojiType = str | disnake.Emoji | disnake.PartialEmoji
