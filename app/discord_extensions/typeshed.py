import typing
from collections import abc

from disnake import Event, Localized

from typeshed import CoroFunc

__all__ = ("AutocompleteReturnType", "ListenerRegistry")

AutocompleteReturnType: typing.TypeAlias = (
    abc.Sequence[str | Localized[str]] | abc.Mapping[str, str | Localized[str]]
)


class ListenerRegistry(typing.Protocol):
    def add_listener(self, func: CoroFunc[typing.Any], /, name: str | Event = ...) -> None:
        ...

    def remove_listener(self, func: CoroFunc[typing.Any], /, name: str | Event = ...) -> None:
        ...
