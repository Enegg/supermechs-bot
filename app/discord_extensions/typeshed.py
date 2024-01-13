import typing as t

from disnake import Event, Localized

from typeshed import CoroFunc

__all__ = ("AutocompleteReturnType", "ListenerRegistry")

AutocompleteReturnType: t.TypeAlias = (
    t.Sequence[str | Localized[str]] | t.Mapping[str, str | Localized[str]]
)


class ListenerRegistry(t.Protocol):
    def add_listener(self, func: CoroFunc[t.Any], /, name: str | Event = ...) -> None:
        ...

    def remove_listener(self, func: CoroFunc[t.Any], /, name: str | Event = ...) -> None:
        ...
