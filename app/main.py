from __future__ import annotations

import logging
import os
from functools import partial

import disnake.voice_client
from disnake import AllowedMentions, Game, Intents
from disnake.ext.commands import InteractionBot
from dotenv import load_dotenv

import i18n
from bridges import register_injections, register_listeners
from config import DATE_FORMAT, DEFAULT_PACK_URL, HOME_GUILD_ID, LOGS_CHANNEL_ID, TEST_GUILDS
from library_extensions import load_extensions, setup_channel_logger
from managers import load_default_pack
from shared.session import IO_CLIENT, create_client_session

from supermechs import init as sm_init

load_dotenv()

logging.Formatter.default_time_format = DATE_FORMAT
logging.captureWarnings(True)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
stream.setFormatter(logging.Formatter("{asctime} [{levelname}] {name} - {message}", style="{"))
logging.root.setLevel(logging.INFO)
logging.root.addHandler(stream)

disnake.voice_client.VoiceClient.warn_nacl = False
logging.getLogger("disnake").setLevel(logging.ERROR)
logging.getLogger("disnake.client").setLevel(logging.CRITICAL)  # mute connection errors


async def main() -> None:
    bot = InteractionBot(
        intents=Intents(guilds=True),
        activity=Game("SuperMechs"),
        allowed_mentions=AllowedMentions.none(),
        localization_provider=i18n.localization_provider,
        test_guilds=TEST_GUILDS if __debug__ else None,
    )
    if __debug__:
        bot.get_global_command_named = partial(bot.get_guild_command_named, HOME_GUILD_ID)

    i18n.load("locale/")
    register_listeners(bot)
    register_injections()
    await sm_init()
    load_extensions(bot.load_extension, "extensions")
    await bot.login(os.environ["TOKEN_DEV" if __debug__ else "TOKEN"])
    await setup_channel_logger(bot, LOGS_CHANNEL_ID, logging.root)

    async with create_client_session(bot.http) as session:
        IO_CLIENT.set(session)
        await load_default_pack(DEFAULT_PACK_URL)
        await bot.connect()


if __name__ == "__main__":
    import anyio

    try:
        anyio.run(main)

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
