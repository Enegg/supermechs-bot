from collections import abc
from typing import Final, Literal

from discord import markdown as md
from disnake import APISlashCommand
from disnake.ext import commands

type CommandName = Literal["item", "legacy-item"]
_COMMAND_MENTIONS: Final[abc.Mapping[CommandName, str]] = {}


def get_mention(name: CommandName, /) -> str:
    mention = _COMMAND_MENTIONS.get(name)

    if mention is not None:
        return mention

    return f"/{name}"


async def populate(bot: commands.InteractionBot, /) -> None:
    from . import sync

    await sync.SYNC_FINISHED.wait()

    for name in _COMMAND_MENTIONS:
        command = bot.get_global_command_named(name)

        if command is None:
            continue

        assert isinstance(command, APISlashCommand)

        _COMMAND_MENTIONS[name] = md.command_mention(command)
