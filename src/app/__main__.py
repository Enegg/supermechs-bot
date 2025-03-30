import logging
import signal
from functools import partial

import anyio
import anyio.abc

import disnake
from discord import load_extensions
from disnake.ext import commands

from app import i18n, paths, state
from app.commands import cancellation, exception_handling
from app.commands.injections import register_injections
from app.core import CONFIG, config_logging, http


def install_signal_handler(bot: commands.InteractionBot, tg: anyio.abc.TaskGroup) -> None:
    # NOTE: anyio.open_signal_receiver does not work on Windows
    def handle(signum: int, frame: object) -> None:
        del frame
        sig = signal.Signals(signum).name
        logging.warning("Received %s, stopping", sig)
        tg.start_soon(bot.close)

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)
    logging.info(
        "Ctrl+C handler installed;"
        " bot should shutdown gracefully, but won't stop loops outside python!"
    )


async def main() -> None:
    from app.commands import sync

    config_logging(paths.CONFIG_TOML)
    disnake.VoiceClient.warn_nacl = False

    bot = commands.InteractionBot(
        # NOTE: guilds provides things like Interaction.me,
        # which is typed as -> Member | ClientUser, but can actually be None
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=i18n.localization_provider,
        test_guilds=CONFIG.test_guild_ids if CONFIG.indev else None,
        command_sync_flags=commands.CommandSyncFlags(
            allow_command_deletion=False,
            sync_commands_debug=CONFIG.debug_command_sync,
            sync_on_cog_actions=False,
        ),
    )
    if CONFIG.indev:
        bot.get_global_command_named = partial(bot.get_guild_command_named, CONFIG.home_guild_id)

    sync.prevent_delayed_sync(bot)
    i18n.load(paths.LOCALE_DIR)
    partial_state = state.load(paths.STATE_DIR)

    register_injections()
    load_extensions(bot.load_extension, "extensions", strict=not CONFIG.indev)
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, CONFIG.bot_token)

    cancellation.setup(bot)
    exception_handling.setup(bot)

    if CONFIG.logs_channel_id is not None:
        await exception_handling.setup_channel(bot, CONFIG.logs_channel_id)

    try:
        async with http.client_session(bot.http) as session, anyio.create_task_group() as tg:
            install_signal_handler(bot, tg)
            tg.start_soon(state.load_async, session, partial_state)
            tg.start_soon(sync.sync_commands, bot)
            tg.start_soon(bot.connect)

    finally:
        state.save(paths.STATE_DIR)


if __name__ == "__main__":
    try:
        anyio.run(main)

    finally:
        logging.shutdown()
