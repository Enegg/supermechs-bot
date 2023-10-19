import typing as t
import typing_extensions as tex
from configparser import ConfigParser

__all__ = ("DATE_FORMAT", "DEFAULT_PACK_URL", "HOME_GUILD_ID", "LOGS_CHANNEL_ID", "TEST_GUILDS")

_parser = ConfigParser()
_parser.read("config.ini")

LOGS_CHANNEL_ID: int = _parser.getint("bot", "LOGS_CHANNEL_ID")
"""The ID of a text channel for ChannelHandler to send logs to."""
HOME_GUILD_ID: int = _parser.getint("bot", "HOME_GUILD_ID")
"""The bot's home guild ID."""
TEST_GUILDS: t.Sequence[int] = (HOME_GUILD_ID,)
"""The IDs of guilds the bot will register commands in while in dev mode."""
DATE_FORMAT: tex.LiteralString = "%d.%m.%Y %H:%M:%S"
DEFAULT_PACK_URL: str = _parser.get("SM", "PACK_URL")

del _parser
