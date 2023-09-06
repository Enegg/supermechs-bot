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

from bridges import register_injections, register_listeners
from config import DATE_FORMAT, HOME_GUILD_ID, LOGS_CHANNEL, TEST_GUILDS
from library_extensions import load_extensions, setup_channel_logger
from shared import SESSION_CTX

if t.TYPE_CHECKING:
    from disnake.http import HTTPClient

load_dotenv()

logging.Formatter.default_time_format = DATE_FORMAT
logging.captureWarnings(True)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)

if __debug__:
    log_format = "{asctime} [{levelname}] {name} - {message}"

else:
    # don't append timestamp as heroku does that already
    log_format = "[{levelname}] {name} - {message}"

stream.setFormatter(logging.Formatter(log_format, style="{"))
logging.root.setLevel(logging.INFO)
logging.root.addHandler(stream)

logging.getLogger("disnake").setLevel(logging.ERROR)
logging.getLogger("disnake.client").setLevel(logging.CRITICAL)  # mute connection errors

START_TIME = utcnow()


@contextlib.asynccontextmanager
async def create_aiohttp_session(client: HTTPClient, /) -> t.AsyncIterator[ClientSession]:
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
    register_listeners(bot)
    register_injections()
    load_extensions(bot.load_extension, "extensions")
    await bot.login(os.environ["TOKEN_DEV" if __debug__ else "TOKEN"])
    await setup_channel_logger(bot, LOGS_CHANNEL, logging.root)

    async with create_aiohttp_session(bot.http) as session:
        SESSION_CTX.set(session)
        # await client.fetch_default_item_pack()
        await bot.connect()


if __name__ == "__main__":
    try:
        anyio.run(main)

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()