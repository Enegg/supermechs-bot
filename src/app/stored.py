from factories import player_factory

from memo import Memo

__all__ = ("players",)

players = Memo(player_factory, lambda user: user.id)
