import logging
from functools import partial

import anyio

import disnake
from discord import load_extensions
from disnake.ext import commands

from app import i18n, paths
from app.commands.injectors import register_injections
from app.core import CONFIG, config_logging, http
from app.local_storage import load_default_pack, load_state, save_state


async def main() -> None:
    from app import sync

    config_logging(paths.CONFIG_TOML)
    disnake.VoiceClient.warn_nacl = False

    bot = commands.InteractionBot(
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=i18n.localization_provider,
        test_guilds=CONFIG.test_guild_ids if CONFIG.indev else None,
        command_sync_flags=commands.CommandSyncFlags(
            sync_commands_debug=CONFIG.debug_command_sync,
            sync_on_cog_actions=False,
        ),
    )
    if CONFIG.indev:
        bot.get_global_command_named = partial(bot.get_guild_command_named, CONFIG.home_guild_id)

    sync.patch_delayed_sync(bot)
    i18n.load(paths.LOCALE_DIR)
    register_injections()
    load_extensions(bot.load_extension, "extensions")
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, CONFIG.bot_token)
    await load_state(paths.STATE_DIR)

    async with http.client_session(bot.http) as session, anyio.create_task_group() as tg:
        tg.start_soon(load_default_pack, session)
        tg.start_soon(sync.sync_commands, bot)
        tg.start_soon(bot.connect)

    await save_state(paths.STATE_DIR)


if __name__ == "__main__":
    try:
        anyio.run(main)

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
