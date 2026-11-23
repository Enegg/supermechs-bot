import asyncio
import logging
import signal
from collections import abc
from functools import partial
from typing import override

import anyio

import disnake
from disnake import Client, LocalizationProtocol
from disnake.ext import commands

from app import aio, init, paths
from app.core.config import CONFIG
from app.core.state import I18nStore, State

_LOG = logging.getLogger("main")


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
                    self._LOG.debug("Localizations not found for key %r", key)

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
    init.setup_event_listeners(bot, state)
    init.load_plugins(paths.PLUGINS_PACKAGE, state)

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
            if not bot.is_closed():
                tg.start_soon(Client.close, bot)

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
