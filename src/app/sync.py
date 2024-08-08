import logging

import anyio

from disnake.ext import commands

_LOGGER = logging.getLogger(__name__)
_SYNC_GUARD = anyio.ResourceGuard("syncing")
SYNC_FINISHED = anyio.Event()


def patch_delayed_sync(bot: commands.InteractionBot, /) -> None:
    """Patches delayed sync not to fire."""
    # this patch has to be done mostly because plugins call this method with no opt-out
    bot._schedule_delayed_command_sync = lambda: None  # pyright: ignore[reportPrivateUsage]


async def sync_commands(bot: commands.InteractionBot, /) -> None:
    with _SYNC_GUARD:
        _LOGGER.info("Command sync initiated")
        await bot._prepare_application_commands()  # pyright: ignore[reportPrivateUsage]
        SYNC_FINISHED.set()
        _LOGGER.info("Command sync finished")
