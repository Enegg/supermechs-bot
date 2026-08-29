import asyncio
import logging
import signal
from functools import partial

import anyio
import anyio.abc

import disnake
from app.disnake_types import CommandInteraction
from discord import load_extensions
from disnake.ext import commands

from app import aio, i18n, paths
from app.commands import exception_handling, mentions
from app.core import CONFIG, config_logging
from app.managers import loader

_LOG = logging.getLogger("main")
_LOG_EVENT = logging.getLogger("event")


def setup_event_loggers(client: disnake.Client, /) -> None:
    @client.listen(disnake.Event.ready)
    async def _() -> None:
        limit = client.session_start_limit
        assert limit is not None
        _LOG.info(
            f"Username: {client.user.name};"
            f" Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
        )

    @client.listen(disnake.Event.disconnect)
    async def _() -> None:
        _LOG.info("Disconnected")

    @client.listen(disnake.Event.slash_command)
    async def _(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        _LOG.info(
            "%s (%d): /%s",
            inter.author.name,
            inter.author.id,
            command_name,
            extra={"filled_options": inter.filled_options},
        )

    @client.listen(disnake.Event.slash_command_completion)
    async def _(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        result = "failed" if inter.command_failed else "finished"
        _LOG.info("Command by %s %s: /%s", inter.author, result, command_name)


def setup_signal_handler(client: disnake.Client, tg: anyio.abc.TaskGroup) -> None:
    # TODO: cancel all ongoing commands before .close
    # NOTE: anyio.open_signal_receiver does not work on Windows
    def handle(signum: int, frame: object) -> None:
        del frame
        sig = signal.Signals(signum).name
        _LOG.warning("Received %s, stopping", sig)
        tg.start_soon(client.close)

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)


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
        bot.get_global_command_named = partial(bot.get_guild_command_named, CONFIG.dev_guild_id)

    sync.prevent_delayed_sync(bot)
    i18n.load(paths.LOCALE_DIR)
    setup_event_loggers(bot)
    exception_handling.setup(bot)

    load_extensions(bot.load_extension, paths.PLUGINS_PACKAGE)
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, CONFIG.bot_token)

    if CONFIG.logs_channel_id:
        await exception_handling.setup_channel(bot, CONFIG.logs_channel_id)

    else:
        _LOG.info(f"{CONFIG.logs_channel_id=}, channel logging disabled")

    async with aio.client_session(bot.http), anyio.create_task_group() as tg:
        setup_signal_handler(bot, tg)

        if CONFIG.item_pack_uri is None:
            _LOG.warning(f"{CONFIG.item_pack_uri=}, item pack not configured")
        else:
            tg.start_soon(loader.load_datapack, CONFIG.item_pack_uri, CONFIG.gfx_pack_uri)

        tg.start_soon(sync.sync_commands, bot)
        tg.start_soon(mentions.populate, bot)
        tg.start_soon(bot.connect)


if __name__ == "__main__":
    try:
        anyio.run(main)

    finally:
        logging.shutdown()
