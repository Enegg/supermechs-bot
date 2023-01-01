import typing as t

from SuperMechs.player import Player

__all__ = ("get_player",)


@t.runtime_checkable
class UserLike(t.Protocol):
    @property
    def id(self) -> int:
        ...

    @property
    def name(self) -> str:
        ...


@t.runtime_checkable
class HasAuthor(t.Protocol):
    @property
    def author(self) -> UserLike:
        ...


def get_player(data: UserLike | HasAuthor, /) -> Player:
    """Return a Player from object containing user ID."""

    if isinstance(data, UserLike):
        id = data.id
        name = data.name

    elif isinstance(data, HasAuthor):
        user = data.author
        id = user.id
        name = user.name

    else:
        raise TypeError(f"{data!r} isn't a user nor has .author attribute")

    return Player.get_cached(id, name)
