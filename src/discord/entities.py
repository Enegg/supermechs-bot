from typing import ClassVar, Final, Protocol, final, override

import msgspec

import disnake
from disnake import PartialEmoji

__all__ = ("AbstractUser", "AnyEmoji", "CustomEmoji", "NullUser", "UnicodeEmoji")


class AbstractUser(Protocol):
    @property
    def id(self) -> int: ...
    @property
    def name(self) -> str: ...
    @property
    def global_name(self) -> str | None: ...
    @property
    def bot(self) -> bool: ...
    @property
    def display_name(self) -> str: ...
    @property
    def mention(self) -> str: ...
    @property
    def avatar(self) -> disnake.Asset | None: ...


@final
class NullUser:
    __slots__ = ()

    id: Final[int] = 0
    name: Final[str] = "Unknown"
    global_name: Final[str | None] = None
    bot: Final[bool] = False
    display_name: Final[str] = name
    assert id is not __builtins__.id, "Fucky wucky uwu"
    mention: Final[str] = f"<@{id}>"
    avatar: Final[disnake.Asset | None] = None


type AnyEmoji = UnicodeEmoji | CustomEmoji


@final
class UnicodeEmoji(msgspec.Struct, frozen=True):
    """Built-in unicode emoji."""

    name: str
    id: ClassVar[Final] = None
    animated: ClassVar[Final] = False

    @override
    def __str__(self) -> str:
        return self.name

    @property
    def mention(self) -> str:
        return self.name

    def to_partial(self) -> PartialEmoji:
        return PartialEmoji(id=None, name=self.name)


@final
class CustomEmoji(msgspec.Struct, frozen=True):
    """Application-owned emoji."""

    id: int
    name: str
    animated: bool = False

    @override
    def __str__(self) -> str:
        if self.animated:
            return f"<a:{self.name}:{self.id}>"
        return f"<:{self.name}:{self.id}>"

    @property
    def mention(self) -> str:
        if self.animated:
            return f"<a:{self.name}:{self.id}>"
        return f"<:{self.name}:{self.id}>"

    def to_partial(self) -> PartialEmoji:
        return PartialEmoji(id=self.id, name=self.name, animated=self.animated)
