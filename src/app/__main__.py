import asyncio
import logging
import signal

import anyio
import anyio.abc

from disnake import Client, Event

from app import aio, i18n, init, paths
from app.commands import exception_handling
from app.core import CONFIG, state
from app.typeshed import CommandInteraction
from app.utils import walk_extensions

_LOG = logging.getLogger("main")
_LOG_EVENT = logging.getLogger("event")


def setup_event_loggers(client: Client, /) -> None:
    @client.listen(Event.ready)
    async def _() -> None:
        limit = client.session_start_limit
        assert limit is not None
        _LOG.info(
            f"Username: {client.user.name};"
            f" Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
        )

    @client.listen(Event.disconnect)
    async def _() -> None:
        _LOG.info("Disconnected")

    @client.listen(Event.slash_command)
    async def _(inter: CommandInteraction, /) -> None:
        command_name = inter.application_command.qualified_name
        _LOG.info(
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
        _LOG.info("Command by %s %s: /%s", inter.author, result, command_name)


def setup_signal_handler(client: Client, tg: anyio.abc.TaskGroup) -> None:
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
    init.config_logging()
    bot = state.BOT
    state.event_loop = bot._connection.loop = bot.http.loop = bot.loop = asyncio.get_running_loop()  # pyright: ignore[reportPrivateUsage]

    i18n.load(paths.LOCALE_DIR)
    setup_event_loggers(bot)
    exception_handling.setup(bot)

    for ext in walk_extensions(paths.PLUGINS_PACKAGE):
        try:
            bot.load_extension(ext)
        except Exception as exc:
            _LOG.error("Ignoring exception in %s:", ext, exc_info=exc)

    # bypass call to _schedule_app_command_preparation
    await Client.login(bot, CONFIG.bot_token)

    if CONFIG.logs_channel_id:
        await init.setup_logs_channel(bot, CONFIG.logs_channel_id)

    else:
        _LOG.info(f"{CONFIG.logs_channel_id=}, channel logging disabled")

    async with (
        aio.client_session(bot.http) as state.http_session,
        anyio.create_task_group() as tg,
    ):
        setup_signal_handler(bot, tg)

        if CONFIG.item_pack_uri is None:
            _LOG.warning(f"{CONFIG.item_pack_uri=}, item pack not configured")
        else:
            tg.start_soon(
                init.load_datapack,
                CONFIG.item_pack_uri,
                CONFIG.gfx_pack_uri,
                state.http_session,
            )

        tg.start_soon(init.sync_commands, bot)
        tg.start_soon(bot.connect)


if __name__ == "__main__":
    try:
        anyio.run(main)

    finally:
        logging.shutdown()
