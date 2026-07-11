import asyncio
import logging
import signal
from functools import partial

import anyio
import anyio.abc

import disnake
from discord import load_extensions
from disnake import Client, Event
from disnake.ext import commands

from app import aio, i18n, init, paths
from app.commands import exception_handling
from app.core import CONFIG, AppState
from app.managers import loader
from app.typeshed import CommandInteraction

_LOG = logging.getLogger("main")
_EVENT_LOG = logging.getLogger("event")


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


def prevent_delayed_sync(bot: commands.InteractionBot, /) -> None:
    """Patches delayed sync not to fire."""
    # this patch has to be done mostly because plugins call this method with no opt-out
    bot._schedule_delayed_command_sync = lambda: None  # pyright: ignore[reportPrivateUsage]


def install_listeners(client: Client, /) -> None:
    @client.listen(Event.ready)
    async def on_ready() -> None:
        limit = AppState.bot.session_start_limit
        assert limit is not None
        _EVENT_LOG.info(
            f"Username: {AppState.bot.user.name};"
            f" Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
        )

    @client.listen(Event.disconnect)
    async def on_disconnect() -> None:
        _EVENT_LOG.info("Disconnected")

    @client.listen(Event.slash_command)
    async def on_slash_command(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        _EVENT_LOG.info(
            "%s (%d): /%s",
            inter.author,
            inter.author.id,
            command_name,
            extra={"filled_options": inter.filled_options},
        )

    @client.listen(Event.slash_command_completion)
    async def on_slash_command_completion(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        result = "failed" if inter.command_failed else "finished"
        _EVENT_LOG.info("Command by %s %s: /%s", inter.author, result, command_name)


async def main() -> None:
    init.config_logging()
    disnake.VoiceClient.warn_nacl = False

    AppState.bot = bot = commands.InteractionBot(
        # NOTE: guilds provides things like Interaction.me,
        # which is typed as -> Member | ClientUser, but can actually be None
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=AppState.I18n.localization_provider,
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

    prevent_delayed_sync(bot)
    i18n.load(paths.LOCALE_DIR)
    exception_handling.setup(bot)
    install_listeners(bot)

    load_extensions(bot.load_extension, paths.PLUGINS_PACKAGE)
    # bypass call to _schedule_app_command_preparation
    await disnake.Client.login(bot, CONFIG.bot_token)

    if CONFIG.logs_channel_id:
        await init.setup_logs_channel(bot, CONFIG.logs_channel_id)

    else:
        _LOG.info(f"{CONFIG.logs_channel_id=}, channel logging disabled")

    async with (
        aio.client_session(bot.http) as AppState.http_session,
        anyio.create_task_group() as tg,
    ):
        setup_signal_handler(bot, tg)

        if CONFIG.item_pack_uri is None:
            _LOG.warning(f"{CONFIG.item_pack_uri=}, item pack not configured")
        else:
            tg.start_soon(
                loader.load_datapack,
                CONFIG.item_pack_uri,
                CONFIG.gfx_pack_uri,
                AppState.http_session,
            )

        tg.start_soon(init.sync_commands, bot)
        tg.start_soon(bot.connect)


if __name__ == "__main__":
    try:
        anyio.run(main)

    finally:
        logging.shutdown()
