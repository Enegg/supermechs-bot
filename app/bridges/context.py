from __future__ import annotations

from attrs import define
from disnake import CommandInteraction

from SuperMechs.api import Player, SMClient

__all__ = ("AppContext",)


@define
class AppContext:
    client: SMClient
    inter: CommandInteraction
    parent: AppContext | None = None

    @property
    def player(self) -> Player:
        return self.client.state.store_player(self.inter.author)

    @property
    def response(self):
        return self.inter.response
