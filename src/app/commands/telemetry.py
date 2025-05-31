from collections import abc, defaultdict, deque
from datetime import datetime
from typing import Final

import attrs

from app.disnake_types import CommandInteraction
from disnake import Event
from disnake.ext import commands

from app.utils import utcnow

__all__ = ()

MAX_HISTORY: Final[int] = 100


@attrs.frozen
class Invocation:
    user_id: int
    date: datetime = attrs.field(factory=utcnow)


@attrs.define
class Invocations:
    total: int = 0
    recent: deque[Invocation] = attrs.field(factory=lambda: deque(maxlen=MAX_HISTORY))

    def add_invocation(self, user_id: int) -> None:
        self.total += 1
        self.recent.append(Invocation(user_id))


_command_invocations: Final[abc.MutableMapping[int, Invocations]] = defaultdict(Invocations)


def iter_invocations() -> abc.Iterator[tuple[int, Invocations]]:
    yield from _command_invocations.items()


def total_invocations() -> int:
    return sum(inv.total for inv in _command_invocations.values())


async def _on_slash_command(inter: CommandInteraction, /) -> None:
    _command_invocations[inter.data.id].add_invocation(inter.user.id)


def setup(bot: commands.InteractionBot, /) -> None:
    bot.add_listener(_on_slash_command, Event.slash_command)
