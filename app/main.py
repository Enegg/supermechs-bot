import logging
import logging.config
from functools import partial

import disnake
from disnake.ext import commands

import i18n
from bridges import register_injections, setup_channel_logger
from config import logging_config
from discord_extensions import load_extensions
from env import ENV
from shared.item_packs import load_default_pack
from shared.session import IO_SESSION, client_session


async def main() -> None:
    logging.captureWarnings(True)
    logging.config.dictConfig(logging_config())
    disnake.VoiceClient.warn_nacl = False

    bot = commands.InteractionBot(
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=i18n.localization_provider,
        test_guilds=ENV.test_guild_ids if __debug__ else None,
    )
    if __debug__:
        bot.get_global_command_named = partial(bot.get_guild_command_named, ENV.home_guild_id)

    i18n.load("locale/")
    register_injections()
    load_extensions(bot.load_extension, "extensions")
    await bot.login(ENV.token)
    await setup_channel_logger(bot, ENV.logs_channel_id)

    async with client_session(bot.http) as session:
        IO_SESSION.set(session)
        await load_default_pack(session)
        await bot.connect()


if __name__ == "__main__":
    import anyio

    try:
        anyio.run(main)

    except (KeyboardInterrupt, anyio.get_cancelled_exc_class()):
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
