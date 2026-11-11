import asyncio
import logging
import signal
from collections import abc
from functools import partial
from typing import override

import anyio

import disnake
from disnake import Client, Event, LocalizationProtocol
from disnake.ext import commands

from app import aio, init, paths
from app.commands import exception_handling
from app.core.config import CONFIG
from app.core.state import I18nStore, State
from app.typeshed import CommandInteraction
from app.utils import walk_extensions

_LOG = logging.getLogger("main")
_LOG_EVENT = logging.getLogger("event")


def setup_event_loggers(client: Client, /) -> None:
    @client.listen(Event.ready)
    async def _() -> None:
        limit = client.session_start_limit
        assert limit is not None
        _LOG_EVENT.info(
            f"Username: {client.user.name};"
            f" Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
        )

    @client.listen(Event.disconnect)
    async def _() -> None:
        _LOG_EVENT.info("Disconnected")

    @client.listen(Event.slash_command)
    async def _(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        _LOG_EVENT.info(
            "%s (%d): /%s",
            inter.author.name,
            inter.author.id,
            command_name,
            extra={"filled_options": inter.filled_options},
        )

    @client.listen(Event.slash_command_completion)
    async def _(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        result = "failed" if inter.command_failed else "finished"
        _LOG_EVENT.info("Command by %s %s: /%s", inter.author, result, command_name)


async def main() -> None:
    init.config_logging()
    i18n = I18nStore()

    l10n_provider: LocalizationProtocol
    if CONFIG.indev:

        class _LogMissingProvider(LocalizationProtocol):
            _LOG = logging.getLogger("app.i18n")

            @override
            def get(self, key: str) -> abc.Mapping[str, str] | None:  # pyright: ignore[reportIncompatibleMethodOverride]
                if (data := i18n.command_l10ns.get(key)) is None:
                    self._LOG.info("Localizations not found for key %r", key)

                return data

        l10n_provider = _LogMissingProvider()

    else:
        # provider only needs .get(_: str, /) -> Mapping[str, str] | None
        l10n_provider = i18n.command_l10ns  # pyright: ignore[reportAssignmentType]

    disnake.VoiceClient.warn_nacl = False
    bot = commands.InteractionBot(
        # NOTE: guilds provides things like Interaction.me,
        # which is typed as -> Member | ClientUser, but can actually be None
        intents=disnake.Intents(guilds=True),
        activity=disnake.Game("SuperMechs"),
        allowed_mentions=disnake.AllowedMentions.none(),
        localization_provider=l10n_provider,
        test_guilds=CONFIG.test_guild_ids if CONFIG.indev else None,
        command_sync_flags=commands.CommandSyncFlags(
            sync_commands_debug=CONFIG.debug_command_sync,
            sync_on_cog_actions=False,
        ),
        loop=asyncio.get_running_loop(),
    )
    if CONFIG.indev:
        bot.get_global_command_named = partial(bot.get_guild_command_named, CONFIG.dev_guild_id)

    # this patch has to be done mostly because plugins call this method with no opt-out
    bot._schedule_delayed_command_sync = lambda: None  # pyright: ignore[reportPrivateUsage]

    State.instance = state = State(bot=bot, i18n=i18n)

    init.load_i18n(paths.LOCALE_DIR, i18n)
    setup_event_loggers(bot)
    exception_handling.setup(state)

    for ext in walk_extensions(paths.PLUGINS_PACKAGE):
        try:
            bot.load_extension(ext)
        except Exception as exc:
            _LOG.error("Ignoring exception in %s:", ext, exc_info=exc)

    # bypass call to _schedule_app_command_preparation
    await Client.login(bot, CONFIG.bot_token)

    if CONFIG.logs_channel_id:
        await init.setup_logs_channel(state, CONFIG.logs_channel_id)

    else:
        _LOG.info(f"{CONFIG.logs_channel_id=}, channel logging disabled")

    async with (
        aio.client_session(bot.http) as http_session,
        anyio.create_task_group() as tg,
    ):
        # ---------------------------------- setup signal handler ----------------------------------
        # NOTE: anyio.open_signal_receiver does not work on Windows
        def handle(signum: int, frame: object) -> None:
            del frame
            sig = signal.Signals(signum).name
            _LOG.warning("Received %s, stopping", sig)
            tg.start_soon(bot.close)

        signal.signal(signal.SIGINT, handle)
        signal.signal(signal.SIGTERM, handle)

        if CONFIG.item_pack_uri is None:
            _LOG.warning(f"{CONFIG.item_pack_uri=}, item pack not configured")
        else:
            tg.start_soon(
                init.load_datapack, CONFIG.item_pack_uri, CONFIG.gfx_pack_uri, state, http_session
            )

        tg.start_soon(init.sync_commands, state)
        tg.start_soon(init.init_app_info, state)
        tg.start_soon(init.init_sloc, state)
        tg.start_soon(bot.connect)


if __name__ == "__main__":
    try:
        anyio.run(main)

    finally:
        logging.shutdown()
