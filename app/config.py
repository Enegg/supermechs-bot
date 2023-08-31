import typing as t
from configparser import ConfigParser

__all__ = ("LOGS_CHANNEL", "HOME_GUILD_ID", "TEST_GUILDS")

_parser = ConfigParser()
_parser.read("config.ini")

LOGS_CHANNEL: int = _parser.getint("bot", "LOGS_CHANNEL")
"""The ID of a text channel for ChannelHandler to send logs to."""

HOME_GUILD_ID: int = _parser.getint("bot", "HOME_GUILD_ID")
"""The bot's home guild ID."""

TEST_GUILDS: t.Sequence[int] = (HOME_GUILD_ID,)
"""The IDs of guilds the bot will register commands in while in dev mode."""
