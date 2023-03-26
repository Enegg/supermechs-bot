from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from functools import partial

from aiohttp import ClientSession, ClientTimeout
from disnake import AllowedMentions, Client, Game, Intents
from disnake.abc import Messageable
from dotenv import load_dotenv

from bot import ModularBot
from bridges import register_injections
from config import LOGS_CHANNEL, TEST_GUILDS
from library_extensions import ChannelHandler, FileRecord
from shared import SESSION_CTX

from SuperMechs.client import SMClient

load_dotenv()

logging.Formatter.default_time_format = "%d.%m.%Y %H:%M:%S"
logging.setLogRecordFactory(FileRecord)
logging.captureWarnings(True)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)

if __debug__:
    format = "{asctime} [{levelname}] {name} - {message}"

else:
    # don't append timestamp as heroku does that already
    format = "[{levelname}] {name} - {message}"

stream.setFormatter(logging.Formatter(format, style="{"))
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.setLevel(logging.INFO)
ROOT_LOGGER.addHandler(stream)

logging.getLogger("disnake").setLevel(logging.ERROR)


@contextlib.asynccontextmanager
async def create_aiohttp_session(client: Client, /):
    """Context manager establishing a client session, reusing client's connector & proxy."""
    async with ClientSession(
        connector=client.http.connector, timeout=ClientTimeout(total=30)
    ) as session:
        session._request = partial(session._request, proxy=client.http.proxy)
        yield session


async def main() -> None:
    client = SMClient()
    bot = ModularBot(
        intents=Intents(guilds=True),
        activity=Game("SuperMechs"),
        test_guilds=TEST_GUILDS if __debug__ else None,
        allowed_mentions=AllowedMentions.none(),
        strict_localization=True,
    )

    bot.i18n.load("locale/")
    register_injections(client)
    bot.load_extensions("extensions")

    async with create_aiohttp_session(bot) as session:
        SESSION_CTX.set(session)
        await bot.login(os.environ["TOKEN_DEV" if __debug__ else "TOKEN"])

        logs_channel = await bot.fetch_channel(LOGS_CHANNEL)
        assert isinstance(logs_channel, Messageable), "Channel is not messageable"
        ROOT_LOGGER.addHandler(ChannelHandler(logs_channel.send, logging.WARNING))
        ROOT_LOGGER.info(f"Warnings+ redirected to {logs_channel}")

        await client.fetch_default_item_pack()
        await bot.connect()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
