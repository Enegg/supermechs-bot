import logging
from functools import partial

import anyio

import disnake
from discord import load_extensions
from disnake.ext import commands

from app import i18n, paths
from app.bridges import register_injections
from app.core import ENV, client_session, config_logging
from app.local_storage import load_default_pack, load_state, save_state
from app.state import state


async def main() -> None:
    from app import sync

    config_logging(paths.CONFIG)
    disnake.VoiceClient.warn_nacl = False

    bot = commands.InteractionBot(
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=i18n.localization_provider,
        test_guilds=ENV.test_guild_ids if __debug__ else None,
        command_sync_flags=commands.CommandSyncFlags(
            sync_commands_debug=__debug__,
            sync_on_cog_actions=False,
        ),
    )
    if __debug__:
        bot.get_global_command_named = partial(bot.get_guild_command_named, ENV.home_guild_id)

    sync.patch_delayed_sync(bot)
    i18n.load(paths.LOCALE)
    register_injections()
    load_extensions(bot.load_extension, "extensions")
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, ENV.token)
    await load_state(paths.STATE)

    async with client_session(bot.http) as session, anyio.create_task_group() as tg:
        state.http_session = session
        tg.start_soon(load_default_pack, session)
        tg.start_soon(sync.sync_commands, bot)
        tg.start_soon(bot.connect)

    await save_state(paths.STATE)


if __name__ == "__main__":
    try:
        anyio.run(main)

    except KeyboardInterrupt:
        # graceful shutdown it is not
        pass

    finally:
        logging.shutdown()
