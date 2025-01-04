from collections import deque
from datetime import datetime
from typing import Final
from typing_extensions import override

import attrs

import disnake
from discord import markdown as md
from disnake.utils import utcnow

__all__ = ("command_tracker",)

MAX_HISTORY: int = 100


@attrs.define(frozen=True)
class Invocation:
    user_id: int
    date: datetime = attrs.field(factory=utcnow)


@attrs.define
class CommandData:
    id: Final[int]
    name: Final[str]
    total_invocations: int = 0
    recent_invocations: deque[Invocation] = attrs.field(factory=lambda: deque(maxlen=MAX_HISTORY))

    @override
    def __str__(self) -> str:
        return md.command_mention(self)


@attrs.define
class CommandTracker:
    commands_data: dict[int, CommandData] = attrs.field(factory=dict)

    def add_invocation(self, inter: disnake.CommandInteraction, /) -> None:
        try:
            data = self.commands_data[inter.data.id]

        except KeyError:
            data = self.commands_data[inter.data.id] = CommandData(
                inter.data.id, inter.application_command.qualified_name
            )

        data.total_invocations += 1
        data.recent_invocations.append(Invocation(inter.user.id))

    def total_invocations(self) -> int:
        return sum(cmd.total_invocations for cmd in self.commands_data.values())


command_tracker: Final = CommandTracker()
