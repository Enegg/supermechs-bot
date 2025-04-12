from collections import abc
from typing import Any, Protocol, runtime_checkable

import disnake

__all__ = (
    "AutocompleteReturnType",
    "EmbedColorType",
    "EmojiType",
    "ListenerRegistry",
)

type CoroFunc[**P, T] = abc.Callable[P, abc.Coroutine[Any, Any, T]]
type AutocompleteReturnType = (
    abc.Sequence[str | disnake.Localized[str]] | abc.Mapping[str, str | disnake.Localized[str]]
)
type EmbedColorType = disnake.Color | int | None
type EmojiType = str | disnake.Emoji | disnake.PartialEmoji


@runtime_checkable
class ListenerRegistry(Protocol):
    def add_listener(
        self, func: CoroFunc[..., None], /, name: str | disnake.Event = ...
    ) -> None: ...

    def remove_listener(
        self, func: CoroFunc[..., None], /, name: str | disnake.Event = ...
    ) -> None: ...
