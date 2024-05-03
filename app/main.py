import logging
import logging.config
from functools import partial

import anyio
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
    import sync

    logging.captureWarnings(True)
    logging.config.dictConfig(logging_config())
    disnake.VoiceClient.warn_nacl = False

    bot = commands.InteractionBot(
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=i18n.localization_provider,
        test_guilds=ENV.test_guild_ids if __debug__ else None,
        command_sync_flags=commands.CommandSyncFlags.none(),  # perform sync myself
    )
    if __debug__:
        bot.get_global_command_named = partial(bot.get_guild_command_named, ENV.home_guild_id)

    sync.patch_delayed_sync(bot)
    i18n.load("locale/")
    register_injections()
    load_extensions(bot.load_extension, "extensions")
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, ENV.token)
    await setup_channel_logger(bot, ENV.logs_channel_id)

    async with client_session(bot.http) as session, anyio.create_task_group() as tg:
        IO_SESSION.set(session)
        tg.start_soon(load_default_pack, session)
        tg.start_soon(sync.sync_commands, bot)
        tg.start_soon(bot.connect)


if __name__ == "__main__":
    try:
        anyio.run(main)

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
