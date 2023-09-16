import typing as t
import typing_extensions as tex
from configparser import ConfigParser

from supermechs.urls import PACK_V1

__all__ = ("DATE_FORMAT", "DEFAULT_PACK", "HOME_GUILD_ID", "LOGS_CHANNEL", "TEST_GUILDS", )

_parser = ConfigParser()
_parser.read("config.ini")

LOGS_CHANNEL: int = _parser.getint("bot", "LOGS_CHANNEL")
"""The ID of a text channel for ChannelHandler to send logs to."""

HOME_GUILD_ID: int = _parser.getint("bot", "HOME_GUILD_ID")
"""The bot's home guild ID."""

TEST_GUILDS: t.Sequence[int] = (HOME_GUILD_ID,)
"""The IDs of guilds the bot will register commands in while in dev mode."""

DATE_FORMAT: tex.LiteralString = "%d.%m.%Y %H:%M:%S"
DEFAULT_PACK: tex.LiteralString = PACK_V1

del _parser
