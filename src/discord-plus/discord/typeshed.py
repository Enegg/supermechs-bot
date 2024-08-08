from collections import abc
from typing import Any, Protocol, TypeAlias, TypedDict, runtime_checkable
from typing_extensions import ParamSpec, TypeVar

import disnake

__all__ = (
    "AutocompleteReturnType",
    "EmbedColorType",
    "EmojiType",
    "ListenerRegistry",
    "SenderKeywords",
)

T = TypeVar("T")
P = ParamSpec("P")

CoroFunc: TypeAlias = abc.Callable[P, abc.Coroutine[Any, Any, T]]
AutocompleteReturnType: TypeAlias = (
    abc.Sequence[str | disnake.Localized[str]] | abc.Mapping[str, str | disnake.Localized[str]]
)
EmbedColorType: TypeAlias = disnake.Color | int | None
EmojiType: TypeAlias = str | disnake.Emoji | disnake.PartialEmoji


@runtime_checkable
class ListenerRegistry(Protocol):
    def add_listener(
        self, func: CoroFunc[..., None], /, name: str | disnake.Event = ...
    ) -> None: ...

    def remove_listener(
        self, func: CoroFunc[..., None], /, name: str | disnake.Event = ...
    ) -> None: ...


class SenderKeywords(TypedDict, total=False):
    content: str
    embed: disnake.Embed
    file: disnake.File
    suppress_embeds: bool
