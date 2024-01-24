import os
import typing as t

import rtoml

from discord_extensions import RESPONSE_TIMEOUT

from supermechs.gamerules import GameRules

__all__ = (
    "DATE_FORMAT",
    "DEFAULT_PACK_URL",
    "HOME_GUILD_ID",
    "LOGS_CHANNEL_ID",
    "TEST_GUILDS",
)

_config = rtoml.load("config.toml")

DATE_FORMAT: str = _config["bot"]["DATE_FORMAT"]
LOGS_CHANNEL_ID: int = int(os.environ["LOGS_CHANNEL_ID"])
"""The ID of a text channel for ChannelHandler to send logs to."""
HOME_GUILD_ID: int = int(os.environ["HOME_GUILD_ID"])
"""The bot's home guild ID."""
TEST_GUILDS: t.Sequence[int] = (HOME_GUILD_ID,)
"""The IDs of guilds the bot will register commands in while in dev mode."""
EMBED_TIPS: t.Sequence[str] = _config["SM"]["EMBED_TIPS"]

DEFAULT_PACK_URL: str = _config["SM"]["DEFAULT_PACK_URL"]

del _config

RESPONSE_TIME_LIMIT: float = RESPONSE_TIMEOUT - 0.5

SM_GAME_RULES = GameRules()
"""The set of rules to use for SuperMechs."""
