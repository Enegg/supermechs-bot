import asyncio
import logging
import signal
from functools import partial

import anyio
import anyio.abc

import disnake
from discord import load_extensions
from disnake.ext import commands

from app import aio, i18n, paths
from app.commands import cancellation, exception_handling, injections, telemetry
from app.core import CONFIG, config_logging
from app.managers import loader

_LOG = logging.getLogger("main")


def setup_signal_handler(bot: disnake.Client, tg: anyio.abc.TaskGroup) -> None:
    # TODO: cancel all ongoing commands before .close
    # NOTE: anyio.open_signal_receiver does not work on Windows
    def handle(signum: int, frame: object) -> None:
        del frame
        sig = signal.Signals(signum).name
        _LOG.warning("Received %s, stopping", sig)
        tg.start_soon(bot.close)

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)
    _LOG.info("Ctrl+C handler installed")


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
            sync_commands_debug=CONFIG.debug_command_sync,
            sync_on_cog_actions=False,
        ),
        # NOTE: Client/Bot instance needs async context. Lets make that clear.
        loop=asyncio.get_running_loop(),
    )
    if CONFIG.indev:
        bot.get_global_command_named = partial(bot.get_guild_command_named, CONFIG.home_guild_id)

    sync.prevent_delayed_sync(bot)
    i18n.load(paths.LOCALE_DIR)
    cancellation.setup(bot)
    exception_handling.setup(bot)
    telemetry.setup(bot)
    injections.register_injections()

    load_extensions(bot.load_extension, "extensions", strict=not CONFIG.indev)
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, CONFIG.bot_token)

    if CONFIG.logs_channel_id:
        await exception_handling.setup_channel(bot, CONFIG.logs_channel_id)

    else:
        _LOG.info(f"{CONFIG.logs_channel_id=}, channel logging disabled")

    async with aio.client_session(bot.http), anyio.create_task_group() as tg:
        setup_signal_handler(bot, tg)

        tg.start_soon(loader.load_datapack)
        tg.start_soon(sync.sync_commands, bot)
        tg.start_soon(bot.connect)


if __name__ == "__main__":
    try:
        anyio.run(main)

    finally:
        logging.shutdown()
