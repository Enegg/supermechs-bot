from typing import final, override

import disnake


@final
class NullUser(disnake.abc.User):
    __slots__ = ()

    id: int = 0
    name: str = "Unknown"
    discriminator: str = "0"
    global_name: str | None = None
    bot: bool = False

    @property
    @override
    def display_name(self) -> str:
        return self.name

    @property
    @override
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    @override
    def avatar(self) -> disnake.Asset | None:
        return None
