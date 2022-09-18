from __future__ import annotations

import typing as t
from configparser import ConfigParser
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from aiohttp import ClientSession


SESSION_CTX: ContextVar["ClientSession"] = ContextVar("session")


parser = ConfigParser()
parser.read("config.ini")

# bot
LOGS_CHANNEL = parser.getint("bot", "LOGS_CHANNEL")
HOME_GUILD_ID = parser.getint("bot", "HOME_GUILD_ID")
TEST_GUILDS = (HOME_GUILD_ID,)
OWNER_ID = parser.getint("bot", "OWNER_ID")

# SM
DEFAULT_PACK_URL = parser["packs"]["DEFAULT_PACK_URL"]
DEFAULT_PACK_V2_URL = parser["packs"]["DEFAULT_PACK_V2_URL"]
WU_SERVER_URL = parser["socket"]["WU_SERVER_URL"]
CLIENT_VERSION = parser["socket"]["CLIENT_VERSION"]
