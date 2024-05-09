import typing
from collections import abc

import disnake

from typeshed import CoroFunc

__all__ = ("AutocompleteReturnType", "ListenerRegistry", "SenderKeywords")

AutocompleteReturnType: typing.TypeAlias = (
    abc.Sequence[str | disnake.Localized[str]] | abc.Mapping[str, str | disnake.Localized[str]]
)
EmojiType: typing.TypeAlias = str | disnake.Emoji | disnake.PartialEmoji


@typing.runtime_checkable
class ListenerRegistry(typing.Protocol):
    def add_listener(self, func: CoroFunc[..., None], /, name: str | disnake.Event = ...) -> None:
        ...

    def remove_listener(
        self, func: CoroFunc[..., None], /, name: str | disnake.Event = ...
    ) -> None:
        ...


class SenderKeywords(typing.TypedDict, total=False):
    content: str
    embed: disnake.Embed
    file: disnake.File
    suppress_embeds: bool
