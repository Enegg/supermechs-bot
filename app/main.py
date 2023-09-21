from __future__ import annotations

import contextlib
import logging
import os
import typing as t
from functools import partial

import anyio
from aiohttp import ClientSession, ClientTimeout
from disnake import AllowedMentions, Game, Intents
from disnake.ext.commands import InteractionBot
from disnake.utils import utcnow
from dotenv import load_dotenv

import i18n
from bridges import register_injections, register_listeners
from config import DATE_FORMAT, DEFAULT_PACK_URL, HOME_GUILD_ID, LOGS_CHANNEL, TEST_GUILDS
from library_extensions import load_extensions, setup_channel_logger
from managers import load_default_pack
from shared import IO_CLIENT

from supermechs import init as sm_init

if t.TYPE_CHECKING:
    from disnake.http import HTTPClient

load_dotenv()

logging.Formatter.default_time_format = DATE_FORMAT
logging.captureWarnings(True)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
stream.setFormatter(logging.Formatter("{asctime} [{levelname}] {name} - {message}", style="{"))
logging.root.setLevel(logging.INFO)
logging.root.addHandler(stream)

logging.getLogger("disnake").setLevel(logging.ERROR)
logging.getLogger("disnake.client").setLevel(logging.CRITICAL)  # mute connection errors

START_TIME = utcnow()


@contextlib.asynccontextmanager
async def create_client_session(client: HTTPClient, /) -> t.AsyncIterator[ClientSession]:
    """Context manager establishing a client session, reusing client's connector & proxy."""
    async with ClientSession(
        connector=client.connector, timeout=ClientTimeout(total=30)
    ) as session:
        session._request = partial(session._request, proxy=client.proxy)
        yield session


async def main() -> None:
    bot = InteractionBot(
        intents=Intents(guilds=True),
        activity=Game("SuperMechs"),
        test_guilds=TEST_GUILDS if __debug__ else None,
        allowed_mentions=AllowedMentions.none(),
        strict_localization=True,
    )
    if __debug__:
        bot.get_global_command_named = partial(bot.get_guild_command_named, HOME_GUILD_ID)

    bot.i18n.load("locale/")
    i18n.load("game_locale/")
    register_listeners(bot)
    register_injections()
    await sm_init()
    load_extensions(bot.load_extension, "extensions")
    await bot.login(os.environ["TOKEN_DEV" if __debug__ else "TOKEN"])
    await setup_channel_logger(bot, LOGS_CHANNEL, logging.root)

    async with create_client_session(bot.http) as session:
        IO_CLIENT.set(session)
        await load_default_pack(DEFAULT_PACK_URL)
        await bot.connect()


if __name__ == "__main__":
    try:
        anyio.run(main)

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
